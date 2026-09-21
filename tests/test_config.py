"""Configuration validation rejects ambiguous units, types and incomplete terms."""
from __future__ import annotations
import copy
import json
import math
import unittest
from pathlib import Path

from clo.inputs import ValidationError, validate_config
from clo.methodology import SOURCE_META

ROOT = Path(__file__).resolve().parents[1]

def valid_config():
    return json.loads((ROOT/'config'/'model.json').read_text(encoding='utf-8'))


class ConfigTests(unittest.TestCase):
    def invalid(self, cfg):
        with self.assertRaises(ValidationError) as caught:
            validate_config(cfg)
        self.assertTrue(caught.exception.issues)
        return caught.exception.issues

    def test_delivered_configuration_valid(self):
        cfg=valid_config()
        self.assertIs(validate_config(cfg),cfg)
        self.assertAlmostEqual(1-cfg['base_senior_pct']-cfg['equity_pct'],.26)

    def test_zero_is_an_explicit_valid_economic_value(self):
        cfg=valid_config()
        for key in ('base_default_rate','recovery_lag_quarters','senior_coupon_bps','junior_coupon_bps',
                    'senior_fee_bps','subordinated_fee_bps','fixed_fee_per_period','annual_prepayment_rate',
                    'reinvestment_recovery','oc_recovery_credit','final_liquidation_price','oc_trigger','ic_trigger'):
            cfg[key]=0
        cfg['index_rate_path']=[0]
        for scenario in cfg['scenarios']:
            scenario['index_rate_path']=[0]
            scenario['recovery_multiplier']=0
            scenario['annual_prepayment_rate']=0
        validate_config(cfg)

    def test_required_scalar_terms_missing(self):
        for key in ('as_of_date','legal_final_date','reinvestment_end_date','base_senior_pct','equity_pct',
                    'base_default_rate','recovery_lag_quarters','starting_cash','periods_per_year',
                    'principal_support_interest','currency','benchmark'):
            with self.subTest(field=key):
                cfg=valid_config();del cfg[key]
                self.invalid(cfg)

    def test_root_must_be_json_object(self):
        for value in (None,[],0,'configuration',True):
            with self.subTest(value=value):self.invalid(value)

    def test_numeric_terms_do_not_accept_strings_boolean_or_nonfinite(self):
        for key in ('base_senior_pct','equity_pct','senior_coupon_bps','recovery_lag_quarters','fixed_fee_per_period'):
            for value in ('0',True,None,float('nan'),float('inf')):
                with self.subTest(field=key,value=value):
                    cfg=valid_config();cfg[key]=value;self.invalid(cfg)

    def test_boolean_not_numeric_zero(self):
        cfg=valid_config();cfg['starting_cash']=False;self.invalid(cfg)

    def test_dates_must_be_canonical_iso_and_chronological(self):
        cases=[('as_of_date','20270101'),('as_of_date','2027-W01-1'),('legal_final_date','2027-01-01'),
               ('reinvestment_end_date','2026-12-31'),('reinvestment_end_date','2040-01-01'),('as_of_date',20270101)]
        for key,value in cases:
            with self.subTest(field=key,value=value):
                cfg=valid_config();cfg[key]=value;self.invalid(cfg)

    def test_capital_stack_ranges_order_and_residual(self):
        cases=[('base_senior_pct',.59),('senior_sizes',[.64,.60]),('senior_sizes',[.64,.64]),
               ('senior_sizes',[.60,.70]),('senior_sizes',[.64,.71]),('equity_pct',.40),('equity_pct',-.01)]
        for key,value in cases:
            with self.subTest(field=key,value=value):
                cfg=valid_config();cfg[key]=value;self.invalid(cfg)

    def test_default_grid_requires_bounds_order_numbers(self):
        for value in ([0,.5], [.5,1], [1,0], [0,.5,.5,1], [False,True], [0,'0.5',1], [], None):
            with self.subTest(value=value):
                cfg=valid_config();cfg['stress_default_rates']=value;self.invalid(cfg)

    def test_rate_path_requires_numeric_array(self):
        for value in (0.03,'0.03',True,{},[True],[0,float('inf')],['0.03'],[]):
            with self.subTest(value=value):
                cfg=valid_config();cfg['index_rate_path']=value;self.invalid(cfg)

    def test_scenarios_require_objects_and_unique_ids(self):
        for value in ([None],[1],['scenario'],[{}],[],{}):
            with self.subTest(value=value):
                cfg=valid_config();cfg['scenarios']=value;self.invalid(cfg)
        cfg=valid_config();cfg['scenarios'][1]['id']=cfg['scenarios'][0]['id'];self.invalid(cfg)

    def test_scenario_nested_weights_rates_and_scalar_types(self):
        cases=[('default_weights',1),('default_weights',{'first':1}),('default_weights',[True]),
               ('default_weights',[-.1,1.1]),('default_weights',[.2,.3]),('index_rate_path',.03),
               ('index_rate_path',[False]),('recovery_multiplier',True),('annual_prepayment_rate',False)]
        for key,value in cases:
            with self.subTest(field=key,value=value):
                cfg=valid_config();cfg['scenarios'][0][key]=value;self.invalid(cfg)

    def test_vocabularies_are_nonempty_text_lists(self):
        for key in ('allowed_industries','allowed_countries','allowed_seniorities'):
            for value in ('US',1,{},[''],[None],[1]):
                with self.subTest(field=key,value=value):
                    cfg=valid_config();cfg[key]=value;self.invalid(cfg)

    def test_currency_and_benchmark_are_text(self):
        for key in ('currency','benchmark'):
            for value in (123,True,['USD'],{'USD':1}):
                with self.subTest(field=key,value=value):
                    cfg=valid_config();cfg[key]=value;self.invalid(cfg)

    def test_mapping_containers_require_objects_of_text(self):
        for key in ('column_mapping','rating_aliases','industry_aliases','country_aliases','seniority_aliases','rate_type_aliases'):
            for value in ([],None,'mapping',{'par':None}):
                with self.subTest(field=key,value=value):
                    cfg=valid_config();cfg[key]=value;self.invalid(cfg)

    def test_unit_multipliers_are_explicit_positive_numeric_fields(self):
        for value in ([],None,{'par':True},{'par':0},{'par':-1},{'par':'1000'},{'unknown':1000}):
            with self.subTest(value=value):
                cfg=valid_config();cfg['unit_multipliers']=value;self.invalid(cfg)
        cfg=valid_config();cfg['unit_multipliers']={'par':1000,'recovery_aaa':.01};validate_config(cfg)

    def test_external_sdr_requires_nonplaceholder_provenance(self):
        cfg=valid_config();cfg['agency_sdr_aaa']=.35
        self.invalid(cfg)
        cfg.update(agency_sdr_source='Imported approved agency output',
                   agency_sdr_portfolio_hash='a'*64, agency_sdr_credit_hash='b'*64,
                   agency_sdr_as_of=cfg['as_of_date'],agency_sdr_criteria_revision=SOURCE_META['republication'],
                   agency_sdr_model_version='Fictional validator test version')
        validate_config(cfg)
        for key in ('agency_sdr_portfolio_hash','agency_sdr_credit_hash'):
            for value in ('',None,'a'*63,'g'*64,123):
                with self.subTest(field=key,value=value):
                    bad=copy.deepcopy(cfg);bad[key]=value;self.invalid(bad)
        cfg['agency_sdr_aaa']=35;self.invalid(cfg)

    def test_nested_scenario_identifiers_and_labels_are_text(self):
        for key in ('id','label'):
            for value in (None,123,True,[],{},''):
                with self.subTest(field=key,value=value):
                    cfg=valid_config();cfg['scenarios'][0][key]=value;self.invalid(cfg)

    def test_invalid_nan_diagnostic_is_json_serializable(self):
        cfg=valid_config();cfg['base_default_rate']=float('nan')
        issues=self.invalid(cfg)
        encoded=json.dumps(issues,allow_nan=False)
        self.assertIn('base_default_rate',encoded)

if __name__=='__main__':unittest.main()
