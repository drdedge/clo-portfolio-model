"""Local runner acceptance, failure preservation and literal Excel import tests."""
from __future__ import annotations
import contextlib
import copy
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from clo.__main__ import (SCALAR_ASSUMPTIONS, SCENARIO_ASSUMPTIONS, finalize_xlsx,
                          import_assumptions, main, validate_external_sdr)
from clo.inputs import ValidationError, digest, load_portfolio, validate_config
from clo.methodology import SOURCE_META

ROOT=Path(__file__).resolve().parents[1]

def config():
    return json.loads((ROOT/'config'/'model.json').read_text(encoding='utf-8'))

def small_config():
    cfg=config()
    cfg['senior_sizes']=[.64]
    cfg['stress_default_rates']=[0,1]
    cfg['scenarios']=cfg['scenarios'][:1]
    cfg['scenarios'][0]['default_weights']=[1]
    cfg['scenarios'][0]['index_rate_path']=[.03]
    return cfg

class Sheet:
    def __init__(self,rows):self.rows=rows
    def iter_rows(self,**kwargs):return iter(self.rows)

class Workbook:
    def __init__(self,assumptions,stress):
        self.sheetnames=['Assumptions','Stress Inputs']
        self.sheets={'Assumptions':Sheet(assumptions),'Stress Inputs':Sheet(stress)}
        self.closed=False
    def __getitem__(self,key):return self.sheets[key]
    def close(self):self.closed=True


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.output=self.folder/'model.xlsx'
        self.output.write_bytes(b'EXISTING WORKBOOK SENTINEL')
        self.config_path=self.folder/'config.json'
        self.config_path.write_text(json.dumps(config()),encoding='utf-8')

    def run_cli(self,*extra,portfolio='example.csv',cfg=None,timeout=60):
        return subprocess.run([sys.executable,'-m','clo','--portfolio',str(ROOT/'examples'/portfolio),
                               '--config',str(cfg or self.config_path),'--output',str(self.output),*extra],
                              cwd=ROOT,capture_output=True,text=True,timeout=timeout)

    def assert_preserved(self):self.assertEqual(self.output.read_bytes(),b'EXISTING WORKBOOK SENTINEL')
    def report(self):return json.loads(self.output.with_suffix('.validation.json').read_text(encoding='utf-8'))

    def test_validate_only_actual_example_has_no_renderer_or_results(self):
        done=self.run_cli('--validate-only')
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertEqual(self.report()['source_rows'],282)
        self.assertEqual(self.report()['obligors'],270)
        self.assert_preserved()
        self.assertFalse(self.output.with_suffix('.results.json').exists())

    def test_validate_only_cannot_be_bypassed_by_template_flag(self):
        done=self.run_cli('--validate-only','--template')
        self.assertEqual(done.returncode,2)
        self.assert_preserved()
        self.assertFalse(self.output.with_suffix('.results.json').exists())

    def test_invalid_csv_keeps_existing_output_and_results(self):
        results=self.output.with_suffix('.results.json');results.write_text('PRIOR RESULTS')
        done=self.run_cli('--validate-only',portfolio='invalid.csv')
        self.assertEqual(done.returncode,2,done.stderr);self.assert_preserved()
        self.assertEqual(results.read_text(),'PRIOR RESULTS')
        self.assertEqual(self.report()['status'],'invalid')
        self.assertFalse(self.report()['workbook_written'])

    def test_malformed_json_fails_cleanly_and_preserves_output(self):
        self.config_path.write_text('{not valid json',encoding='utf-8')
        done=self.run_cli('--validate-only')
        self.assertNotEqual(done.returncode,0);self.assertNotIn('Traceback',done.stderr)
        self.assert_preserved();self.assertEqual(self.report()['status'],'failed')

    def test_wrong_shape_json_config_fails_cleanly(self):
        for value in (None,[],{'scenarios':[1]}):
            with self.subTest(value=value):
                self.config_path.write_text(json.dumps(value),encoding='utf-8')
                done=self.run_cli('--validate-only')
                self.assertNotEqual(done.returncode,0);self.assertNotIn('Traceback',done.stderr)
                self.assert_preserved();self.assertIn(self.report()['status'],('invalid','failed'))

    def test_nonfinite_config_writes_readable_failure_report(self):
        cfg=config();cfg['base_default_rate']=float('nan')
        self.config_path.write_text(json.dumps(cfg),encoding='utf-8')
        done=self.run_cli('--validate-only')
        self.assertNotEqual(done.returncode,0);self.assertNotIn('Traceback',done.stderr)
        self.assert_preserved();self.assertIn(self.report()['status'],('invalid','failed'))

    def test_report_path_cannot_overwrite_input_configuration(self):
        conflicting=self.output.with_suffix('.validation.json')
        original=json.dumps(config());conflicting.write_text(original,encoding='utf-8')
        done=self.run_cli('--validate-only',cfg=conflicting)
        self.assertNotEqual(done.returncode,0)
        self.assertEqual(conflicting.read_text(encoding='utf-8'),original)
        self.assert_preserved()

    def test_engine_only_actual_example_creates_local_results(self):
        self.config_path.write_text(json.dumps(small_config()),encoding='utf-8')
        done=self.run_cli('--engine-only')
        self.assertEqual(done.returncode,0,done.stderr)
        self.assert_preserved()
        packet=json.loads(self.output.with_suffix('.results.json').read_text(encoding='utf-8'))
        self.assertEqual(packet['portfolio']['source_rows'],282)
        self.assertEqual(packet['analytics']['total_par'],300_000_000)
        self.assertEqual(len(packet['portfolio']['source_hash']),64)
        self.assertEqual(packet['analysis']['base_run']['summary']['accounting_valid'],True)
        self.assertEqual(packet['config_hash'],self.report()['config_hash'])

    def test_validate_only_rejects_malformed_fitch_sidecar_and_preserves_results(self):
        sidecar=self.folder/'fitch_inputs.csv'
        results=self.output.with_suffix('.results.json');results.write_text('PRIOR RESULTS')
        cases=(
            ('instrument_id,fitch_rating_typo\nSYN-LN-00001,B\n','fitch_rating_typo'),
            ('instrument_id,fitch_recovery\nSYN-LN-00001,65\n','fitch_recovery'),
            ('instrument_id,fitch_idr\nSYN-LN-00001,B\nSYN-LN-00001,B\n','instrument_id'),
        )
        for contents,field in cases:
            with self.subTest(field=field):
                sidecar.write_text(contents,encoding='utf-8')
                before=sidecar.read_bytes()
                done=self.run_cli('--validate-only','--fitch-inputs',str(sidecar))
                self.assertEqual(done.returncode,2,done.stderr)
                self.assert_preserved();self.assertEqual(results.read_text(),'PRIOR RESULTS')
                self.assertEqual(sidecar.read_bytes(),before)
                self.assertEqual(self.report()['status'],'invalid')
                self.assertFalse(self.report()['workbook_written'])
                self.assertTrue(any(issue['field']==field for issue in self.report()['errors']))

    def test_fitch_input_cannot_be_overwritten_by_any_output_path(self):
        destinations=(self.output,self.output.with_suffix('.results.json'),
                      self.output.with_suffix('.validation.json'))
        for destination in destinations:
            if not destination.exists():destination.write_bytes(b'PRIOR ARTIFACT')
        for conflicting in destinations:
            with self.subTest(path=conflicting.name):
                conflicting.write_text('instrument_id,fitch_idr\nSYN-LN-00001,B\n',encoding='utf-8')
                before={destination:destination.read_bytes() for destination in destinations}
                done=self.run_cli('--validate-only','--fitch-inputs',str(conflicting))
                self.assertEqual(done.returncode,2,done.stderr)
                self.assertIn('Input/output path conflict',done.stderr)
                for destination in destinations:
                    self.assertEqual(destination.read_bytes(),before[destination])

    def test_optional_fitch_sidecar_is_distinct_from_sp_inputs_and_cashflow(self):
        self.config_path.write_text(json.dumps(small_config()),encoding='utf-8')
        done=self.run_cli('--engine-only')
        self.assertEqual(done.returncode,0,done.stderr)
        result_path=self.output.with_suffix('.results.json')
        without=json.loads(result_path.read_text(encoding='utf-8'))
        missing=without['fitch']
        self.assertIsNone(missing['source_hash']);self.assertIsNone(missing['source_path'])
        self.assertIsNone(missing['warf']);self.assertIsNone(missing['warr'])
        self.assertEqual(missing['coverage']['rating_pct'],0)
        self.assertEqual(missing['coverage']['recovery_pct'],0)
        self.assertTrue(missing['missing_inputs'])
        self.assertTrue(all(row['fitch_idr']=='' and row['fitch_recovery'] is None for row in missing['rows']))

        sidecar=ROOT/'examples'/'fitch_example.csv'
        done=self.run_cli('--engine-only','--fitch-inputs',str(sidecar))
        self.assertEqual(done.returncode,0,done.stderr);self.assert_preserved()
        supplied=json.loads(result_path.read_text(encoding='utf-8'))
        metrics=supplied['fitch']
        self.assertEqual(metrics['source_hash'],hashlib.sha256(sidecar.read_bytes()).hexdigest())
        self.assertEqual(metrics['source_path'],str(sidecar.resolve()))
        self.assertEqual(metrics['source_name'],sidecar.name)
        self.assertEqual(metrics['coverage']['rating_pct'],1)
        self.assertTrue(metrics['coverage']['rating_assumed'])
        self.assertGreater(metrics['warf'],0)
        self.assertIn('development assumptions',metrics['warf_status'])
        self.assertIsNone(metrics['warr'])  # Fictional sidecar deliberately leaves ambiguous recoveries missing.
        self.assertLess(metrics['coverage']['recovery_pct'],1)
        for key in ('rdr','rrr','rlr'):self.assertIsNone(metrics[key])
        for key in ('portfolio','config_hash','credit_quality','analysis'):
            self.assertEqual(supplied[key],without[key],key)
        self.assertNotEqual(supplied['run_id'],without['run_id'])

    def test_renderer_failure_keeps_completed_artifacts(self):
        self.config_path.write_text(json.dumps(small_config()),encoding='utf-8')
        results=self.output.with_suffix('.results.json');results.write_text('PRIOR RESULTS')
        with patch('clo.__main__.render',side_effect=RuntimeError('Controlled local renderer failure')):
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                code=main(['--portfolio',str(ROOT/'examples'/'replacement.csv'),'--config',str(self.config_path),'--output',str(self.output)])
        self.assertEqual(code,1);self.assert_preserved();self.assertEqual(results.read_text(),'PRIOR RESULTS')
        self.assertFalse(self.report()['workbook_written'])

    def test_result_publish_failure_keeps_completed_workbook_and_results(self):
        self.config_path.write_text(json.dumps(small_config()),encoding='utf-8')
        results=self.output.with_suffix('.results.json');results.write_text('PRIOR RESULTS')
        original_replace=os.replace
        def controlled_replace(source,destination):
            if Path(destination)==results:
                raise PermissionError('Controlled result-file replacement failure')
            return original_replace(source,destination)
        def fake_render(packet,output,*args):
            Path(output).write_bytes(b'NEW WORKBOOK')
        with patch('clo.__main__.render',side_effect=fake_render),patch('clo.__main__.finalize_xlsx'),patch('clo.__main__.os.replace',side_effect=controlled_replace):
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                code=main(['--portfolio',str(ROOT/'examples'/'replacement.csv'),'--config',str(self.config_path),'--output',str(self.output)])
        self.assertNotEqual(code,0)
        self.assert_preserved();self.assertEqual(results.read_text(),'PRIOR RESULTS')

    def test_workbook_publish_failure_rolls_back_already_published_results(self):
        self.config_path.write_text(json.dumps(small_config()),encoding='utf-8')
        results=self.output.with_suffix('.results.json');results.write_text('PRIOR RESULTS')
        original_replace=os.replace
        def controlled_replace(source,destination):
            if Path(destination)==self.output:
                raise PermissionError('Controlled workbook replacement failure')
            return original_replace(source,destination)
        def fake_render(packet,output,*args):Path(output).write_bytes(b'NEW WORKBOOK')
        with patch('clo.__main__.render',side_effect=fake_render),patch('clo.__main__.finalize_xlsx'),patch('clo.__main__.os.replace',side_effect=controlled_replace):
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                code=main(['--portfolio',str(ROOT/'examples'/'replacement.csv'),'--config',str(self.config_path),'--output',str(self.output)])
        self.assertNotEqual(code,0);self.assert_preserved();self.assertEqual(results.read_text(),'PRIOR RESULTS')

    def test_final_report_publish_failure_rolls_back_both_artifacts(self):
        self.config_path.write_text(json.dumps(small_config()),encoding='utf-8')
        results=self.output.with_suffix('.results.json');results.write_text('PRIOR RESULTS')
        report=self.output.with_suffix('.validation.json')
        original_replace=os.replace
        def controlled_replace(source,destination):
            if Path(destination)==report:raise PermissionError('Controlled report publication failure')
            return original_replace(source,destination)
        def fake_render(packet,output,*args):Path(output).write_bytes(b'NEW WORKBOOK')
        with patch('clo.__main__.render',side_effect=fake_render),patch('clo.__main__.finalize_xlsx'),patch('clo.__main__.os.replace',side_effect=controlled_replace):
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                code=main(['--portfolio',str(ROOT/'examples'/'replacement.csv'),'--config',str(self.config_path),'--output',str(self.output)])
        self.assertNotEqual(code,0);self.assert_preserved();self.assertEqual(results.read_text(),'PRIOR RESULTS')

    def test_external_sdr_for_other_portfolio_is_rejected(self):
        cfg=config();cfg['agency_sdr_aaa']=.3
        cfg['agency_sdr_source']='Fictional imported test output';cfg['agency_sdr_portfolio_hash']='different_hash'
        self.config_path.write_text(json.dumps(cfg),encoding='utf-8')
        done=self.run_cli('--validate-only')
        self.assertEqual(done.returncode,2,done.stderr);self.assert_preserved()
        self.assertTrue(any(e['field']=='agency_sdr_portfolio_hash' for e in self.report()['errors']))

    def test_external_sdr_is_bound_to_normalized_inputs_and_criteria(self):
        cfg=config();portfolio=load_portfolio(ROOT/'examples'/'example.csv',cfg)
        cfg.update(agency_sdr_aaa=.35,agency_sdr_source='Fictional imported test output',
                   agency_sdr_model_version='Fictional test model',agency_sdr_portfolio_hash=portfolio['source_hash'],
                   agency_sdr_as_of=cfg['as_of_date'],agency_sdr_criteria_revision=SOURCE_META['republication'],
                   agency_sdr_credit_hash=digest({'facilities':portfolio['facilities'],'as_of_date':cfg['as_of_date'],
                                                 'criteria_revision':SOURCE_META['republication']}))
        validate_external_sdr(cfg,portfolio)
        for key,value in [('agency_sdr_credit_hash','a'*64),('agency_sdr_as_of','2028-01-01'),
                          ('agency_sdr_criteria_revision','2025-01-01')]:
            with self.subTest(field=key):
                bad=copy.deepcopy(cfg);bad[key]=value
                with self.assertRaises(ValidationError):validate_external_sdr(bad,portfolio)

    def test_finalize_xlsx_sets_recalculation_without_changing_cells(self):
        workbook=b'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets/><extLst/></workbook>'
        sheet=b'<worksheet><c><f>1+1</f><v>2</v></c></worksheet>'
        with zipfile.ZipFile(self.output,'w') as package:
            package.writestr('xl/workbook.xml',workbook)
            package.writestr('xl/worksheets/sheet1.xml',sheet)
        finalize_xlsx(self.output)
        with zipfile.ZipFile(self.output) as package:
            xml=ET.fromstring(package.read('xl/workbook.xml'))
            calc=xml.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}calcPr')
            self.assertEqual(calc.attrib['calcMode'],'auto')
            self.assertEqual(calc.attrib['fullCalcOnLoad'],'1')
            self.assertEqual(calc.attrib['forceFullCalc'],'1')
            self.assertEqual(package.read('xl/worksheets/sheet1.xml'),sheet)
        finalize_xlsx(self.output)
        with zipfile.ZipFile(self.output) as package:
            xml=ET.fromstring(package.read('xl/workbook.xml'))
            self.assertEqual(len(xml.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}calcPr')),1)


class WorkbookAssumptionImportTests(unittest.TestCase):
    def fixture(self,assumptions=None,stress=None,cfg=None):
        cfg=cfg if cfg is not None else small_config()
        overrides=assumptions or []
        override_keys={row[2] for row in overrides if len(row)>2}
        defaults=[(None,None,key,cfg[key]) for key in sorted(SCALAR_ASSUMPTIONS)]
        defaults.extend((None,None,f"scenario.{scenario['id']}.{field}",scenario[field])
                        for scenario in cfg['scenarios'] for field in sorted(SCENARIO_ASSUMPTIONS))
        rows=[row for row in defaults if row[2] not in override_keys]+overrides
        return Workbook(rows,stress if stress is not None else [('front_flat',1,None,1,.03)])

    def import_book(self,book):
        with patch('openpyxl.load_workbook',return_value=book):
            return import_assumptions(small_config(),'in_memory.xlsx')

    def test_literal_dates_and_values_import_without_evaluating_formulas(self):
        book=self.fixture([(None,None,'as_of_date',datetime(2027,1,1)),
                           (None,None,'senior_coupon_bps',175),
                           (None,None,'scenario.front_flat.recovery_multiplier',.8)])
        cfg=self.import_book(book)
        self.assertEqual(cfg['as_of_date'],'2027-01-01')
        self.assertEqual(cfg['senior_coupon_bps'],175)
        self.assertEqual(cfg['scenarios'][0]['recovery_multiplier'],.8)
        self.assertTrue(book.closed)

    def test_complete_untouched_assumptions_preserve_configuration(self):
        self.assertEqual(digest(self.import_book(self.fixture())),digest(small_config()))

    def test_deleted_scalar_row_is_not_replaced_by_configuration(self):
        book=self.fixture()
        book.sheets['Assumptions'].rows=[row for row in book.sheets['Assumptions'].rows
                                        if row[2]!='senior_coupon_bps']
        with self.assertRaises(ValidationError) as failure:self.import_book(book)
        self.assertIn('Missing assumption rows',failure.exception.issues[0]['message'])
        self.assertIn('senior_coupon_bps',failure.exception.issues[0]['message'])
        self.assertTrue(book.closed)

    def test_deleted_dynamic_scenario_row_is_rejected(self):
        cfg=small_config()
        second=copy.deepcopy(cfg['scenarios'][0]);second['id']='second_case'
        cfg['scenarios'].append(second)
        book=self.fixture(cfg=cfg,stress=[('front_flat',1,None,1,.03),('second_case',1,None,1,.03)])
        missing='scenario.second_case.annual_prepayment_rate'
        book.sheets['Assumptions'].rows=[row for row in book.sheets['Assumptions'].rows if row[2]!=missing]
        with patch('openpyxl.load_workbook',return_value=book):
            with self.assertRaises(ValidationError) as failure:import_assumptions(cfg,'in_memory.xlsx')
        self.assertIn(missing,failure.exception.issues[0]['message'])
        self.assertTrue(book.closed)

    def test_formula_in_assumptions_rejected(self):
        with self.assertRaises(ValidationError):
            self.import_book(self.fixture([(None,None,'senior_coupon_bps','=1+1')]))

    def test_numeric_zero_cannot_silently_replace_boolean_assumption(self):
        book=self.fixture([(None,None,'principal_support_interest',1)])
        updated=self.import_book(book)
        self.assertIs(type(updated['principal_support_interest']),int)
        with self.assertRaises(ValidationError):validate_config(updated)

    def test_duplicate_assumption_key_rejected(self):
        with self.assertRaises(ValidationError):
            self.import_book(self.fixture([(None,None,'senior_coupon_bps',150),(None,None,'senior_coupon_bps',200)]))

    def test_invalid_assumption_key_type_is_validation_error(self):
        with self.assertRaises(ValidationError):
            self.import_book(self.fixture([(None,None,123,150)]))

    def test_formula_in_stress_inputs_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.import_book(self.fixture(stress=[('front_flat',1,None,'=1','.03')]))

    def test_duplicate_or_missing_stress_period_rejected(self):
        for stress in ([],[('front_flat',1,None,1,.03),('front_flat',1,None,1,.03)]):
            with self.subTest(stress=stress):
                with self.assertRaises(ValidationError):self.import_book(self.fixture(stress=stress))

    def test_boolean_and_nonfinite_periods_rejected(self):
        for period in (True,float('inf')):
            with self.subTest(period=period):
                with self.assertRaises(ValidationError):
                    self.import_book(self.fixture(stress=[('front_flat',period,None,1,.03)]))

    def test_workbook_closed_on_rejected_import(self):
        book=self.fixture([(None,None,'unknown_key',1)])
        with self.assertRaises(ValidationError):self.import_book(book)
        self.assertTrue(book.closed)

    def test_structural_json_keys_cannot_be_overwritten_by_scalar_cells(self):
        for key in ('scenarios','allowed_industries','unit_multipliers','scenario.front_flat.id'):
            with self.subTest(key=key):
                with self.assertRaises(ValidationError):self.import_book(self.fixture([(None,None,key,'changed')]))

    def test_untouched_padded_curves_preserve_configuration_hash(self):
        cfg=small_config();cfg['scenarios'][0]['default_weights']=[1.0]
        cfg['scenarios'][0]['index_rate_path']=[.03,.03,.03]
        book=self.fixture([(None,None,'senior_floor_pct',0)],
                          [('front_flat',1,None,1,.03),('front_flat',2,None,0,.03),('front_flat',3,None,0,.03)],cfg=cfg)
        with patch('openpyxl.load_workbook',return_value=book):result=import_assumptions(cfg,'in_memory.xlsx')
        self.assertEqual(digest(result),digest(cfg))
        self.assertEqual(len(result['scenarios'][0]['default_weights']),1)

    def test_later_edited_default_weight_extends_curve_and_input_is_not_mutated(self):
        cfg=small_config();cfg['scenarios'][0]['default_weights']=[1.0]
        cfg['scenarios'][0]['index_rate_path']=[.03,.03,.03]
        before=digest(cfg)
        book=self.fixture(stress=[('front_flat',1,None,.5,.03),('front_flat',2,None,0,.03),('front_flat',3,None,.5,.03)])
        with patch('openpyxl.load_workbook',return_value=book):result=import_assumptions(cfg,'in_memory.xlsx')
        self.assertEqual(result['scenarios'][0]['default_weights'],[.5,0,.5])
        self.assertEqual(digest(cfg),before)

if __name__=='__main__':unittest.main()
