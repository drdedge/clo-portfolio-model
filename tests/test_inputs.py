"""Behavioral ingestion tests with independent fixtures and supplied fictional data."""
from __future__ import annotations
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from clo.inputs import FIELDS, ValidationError, load_portfolio, summarize

ROOT = Path(__file__).resolve().parents[1]


class PortfolioInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        with (ROOT / 'examples' / 'example.csv').open(newline='', encoding='utf-8') as stream:
            self.example = list(csv.DictReader(stream))
        self.config = {
            'as_of_date': '2027-01-01', 'currency': 'USD', 'benchmark': 'SOFR',
            'allowed_industries': sorted({r['sp_industry'] for r in self.example}),
            'allowed_countries': sorted({r['country'] for r in self.example}),
            'allowed_seniorities': sorted({r['seniority'] for r in self.example}),
        }

    def write(self, rows, headers=None, filename='portfolio.csv'):
        path = self.folder / filename
        columns = headers or FIELDS
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        return path

    def modified(self, **fields):
        row = dict(self.example[0]); row.update(fields); return row

    def errors(self, rows, config=None):
        with self.assertRaises(ValidationError) as caught:
            load_portfolio(self.write(rows), config or self.config)
        return caught.exception.issues

    def test_supplied_example_reconciles_and_groups_facilities(self):
        loaded = load_portfolio(ROOT / 'examples' / 'example.csv', self.config)
        stats = summarize(loaded['facilities'], self.config)
        self.assertEqual(loaded['source_rows'], 282)
        self.assertEqual(stats['obligor_count'], 270)
        self.assertEqual(stats['total_par'], 300_000_000)
        self.assertEqual(sum(o['facility_count'] == 2 for o in stats['obligors']), 12)
        self.assertEqual(stats['obligors'][0]['par'], 1_224_000)
        self.assertAlmostEqual(stats['weighted_recovery'], 0.3962717333333333)
        self.assertAlmostEqual(stats['weighted_spread_bps'], 288.4695070159345)
        self.assertEqual(len(loaded['source_hash']), 64)

    def test_replacement_changes_row_count_and_keeps_whole_obligors(self):
        loaded = load_portfolio(ROOT / 'examples' / 'replacement.csv', self.config)
        stats = summarize(loaded['facilities'], self.config)
        self.assertEqual(stats['facility_count'], 52)
        self.assertEqual(stats['obligor_count'], 50)
        self.assertEqual(stats['total_par'], 55_744_000)
        self.assertEqual(sum(o['facility_count'] == 2 for o in stats['obligors']), 2)

    def test_larger_replacement_has_no_fixed_row_limit(self):
        rows = [self.modified(instrument_id=f'FAC-{n:05d}', obligor_id=f'OB-{n:05d}',
                              obligor_name=f'Fictional obligor {n}', par=1000000)
                for n in range(601)]
        loaded = load_portfolio(self.write(rows), self.config)
        stats = summarize(loaded['facilities'], self.config)
        self.assertEqual(stats['facility_count'], 601)
        self.assertEqual(stats['obligor_count'], 601)
        self.assertEqual(stats['total_par'], 601_000_000)

    def test_larger_delivered_fixture_preserves_within_copy_grouping(self):
        loaded = load_portfolio(ROOT / 'examples' / 'replacement_large.csv', self.config)
        stats = summarize(loaded['facilities'], self.config)
        self.assertEqual(stats['facility_count'], 564)
        self.assertEqual(stats['obligor_count'], 540)
        self.assertEqual(stats['total_par'], 600_000_000)
        self.assertEqual(sum(o['facility_count'] == 2 for o in stats['obligors']), 24)

    def test_invalid_example_reports_each_deliberate_error(self):
        with self.assertRaises(ValidationError) as caught:
            load_portfolio(ROOT / 'examples' / 'invalid.csv', self.config)
        fields = {i['field'] for i in caught.exception.issues}
        self.assertTrue({'instrument_id','recovery_aaa','sp_rating','maturity_date','par'} <= fields)

    def test_missing_header_blocks(self):
        path = self.write([self.example[0]], [f for f in FIELDS if f != 'obligor_id'])
        with self.assertRaises(ValidationError) as caught:
            load_portfolio(path, self.config)
        self.assertTrue(any(i['field']=='obligor_id' and i['row']==1 for i in caught.exception.issues))

    def test_missing_required_value_is_not_zero(self):
        for field in ('par','recovery_aaa','obligor_id','maturity_date','price'):
            with self.subTest(field=field):
                issues = self.errors([self.modified(**{field:''})])
                self.assertTrue(any(i['field']==field for i in issues))

    def test_conditional_fields_require_the_correct_rate_type(self):
        for field in ('spread_bps','floor_bps','benchmark'):
            with self.subTest(field=field):
                self.assertTrue(any(i['field']==field for i in self.errors([self.modified(**{field:''})])))
        issues = self.errors([self.modified(rate_type='Fixed', spread_bps='', floor_bps='', benchmark='', fixed_coupon_rate='')])
        self.assertTrue(any(i['field']=='fixed_coupon_rate' for i in issues))

    def test_fixed_semiannual_source_fields_are_preserved(self):
        fixed = next(r for r in self.example if r['rate_type']=='Fixed')
        loaded = load_portfolio(self.write([fixed]), self.config)['facilities'][0]
        self.assertEqual(loaded['payment_frequency'], 2)
        self.assertEqual(loaded['fixed_coupon_rate'], float(fixed['fixed_coupon_rate']))
        self.assertIsNone(loaded['spread_bps'])
        self.assertIsNone(loaded['floor_bps'])
        self.assertIsNone(loaded['benchmark'])

    def test_unsupported_payment_frequencies_block(self):
        for frequency in ('1','3','12','2.5'):
            with self.subTest(frequency=frequency):
                self.assertTrue(any(i['field']=='payment_frequency' for i in self.errors([self.modified(payment_frequency=frequency)])))

    def test_duplicate_facility_rejected_but_shared_obligor_allowed(self):
        issues = self.errors([self.example[0], dict(self.example[0])])
        self.assertTrue(any(i['field']=='instrument_id' for i in issues))
        second = self.modified(instrument_id='OTHER-FACILITY', par='500000', recovery_aaa='0.60')
        loaded = load_portfolio(self.write([self.example[0],second]), self.config)
        stats = summarize(loaded['facilities'], self.config)
        self.assertEqual(stats['obligor_count'], 1)
        self.assertEqual(stats['facility_count'], 2)
        self.assertEqual(stats['obligors'][0]['facility_count'], 2)
        self.assertEqual(stats['obligors'][0]['par'], float(self.example[0]['par'])+500000)

    def test_duplicate_diagnostic_retains_original_csv_row_numbers(self):
        rows = [self.modified(instrument_id='INVALID-FIRST', recovery_aaa=''),
                self.modified(instrument_id='DUPLICATE'), self.modified(instrument_id='DUPLICATE')]
        issues = self.errors(rows)
        duplicate = next(i for i in issues if i['field']=='instrument_id')
        self.assertEqual(duplicate['row'], 4)
        self.assertIn('3', duplicate['message'])

    def test_conflicting_obligor_attributes_rejected(self):
        for field,value in [('obligor_name','Different name'),('sp_rating','BBB'),
                            ('sp_industry','Software'),('country','Canada')]:
            with self.subTest(field=field):
                second = self.modified(instrument_id='OTHER-FACILITY', **{field:value})
                issues = self.errors([self.example[0],second])
                self.assertTrue(any(i['field']==field and 'Conflicting' in i['message'] for i in issues))

    def test_distinct_obligor_ids_do_not_merge_on_name(self):
        second = self.modified(instrument_id='SECOND', obligor_id='SECOND-OBLIGOR')
        loaded = load_portfolio(self.write([self.example[0],second]), self.config)
        self.assertEqual(summarize(loaded['facilities'],self.config)['obligor_count'], 2)

    def test_rating_normalization_and_leading_zero_ids(self):
        row = self.modified(instrument_id='000001', obligor_id='000012', sp_rating=' bb− ', currency='usd')
        loaded = load_portfolio(self.write([row]), self.config)
        self.assertEqual(loaded['facilities'][0]['instrument_id'],'000001')
        self.assertEqual(loaded['facilities'][0]['obligor_id'],'000012')
        self.assertEqual(loaded['facilities'][0]['sp_rating'],'BB-')
        self.assertEqual(loaded['facilities'][0]['currency'],'USD')
        self.assertTrue(loaded['normalizations'])

    def test_unknown_and_unsupported_ratings_block(self):
        for rating in ('NOT_A_RATING','CC','C','D','SD','NR'):
            with self.subTest(rating=rating):
                self.assertTrue(any(i['field']=='sp_rating' for i in self.errors([self.modified(sp_rating=rating)])))

    def test_invalid_units_and_nonfinite_numbers_block(self):
        for field,value in [('recovery_aaa','40'),('spread_bps','250bps'),('floor_bps','0%'),
                            ('par','1,000,000'),('par','NaN'),('recovery_aaa','inf'),('par','-1')]:
            with self.subTest(field=field,value=value):
                self.assertTrue(any(i['field']==field for i in self.errors([self.modified(**{field:value})])))
        row=self.modified(rate_type='Fixed',spread_bps='',floor_bps='',benchmark='',fixed_coupon_rate='5')
        self.assertTrue(any(i['field']=='fixed_coupon_rate' for i in self.errors([row])))

    def test_dates_are_strict_iso_and_after_asof(self):
        for value in ('2032-02-30','01/02/2032','2027-01-01','2026-12-31'):
            with self.subTest(value=value):
                self.assertTrue(any(i['field']=='maturity_date' for i in self.errors([self.modified(maturity_date=value)])))

    def test_unknown_categories_and_currency_block(self):
        for field,value in [('country','Unknown country'),('sp_industry','Unknown industry'),
                            ('seniority','Unknown lien'),('currency','EUR'),('benchmark','OTHER')]:
            with self.subTest(field=field):
                self.assertTrue(any(i['field']==field for i in self.errors([self.modified(**{field:value})])))

    def test_original_source_headers_map_without_code_change(self):
        mapping = json.loads((ROOT/'examples'/'column_mapping.json').read_text())['column_mapping']
        source = {mapping[k]:v for k,v in self.example[0].items()}
        cfg = copy.deepcopy(self.config); cfg['column_mapping']=mapping
        loaded = load_portfolio(self.write([source],list(mapping.values())),cfg)
        self.assertEqual(loaded['facilities'][0]['instrument_id'],self.example[0]['instrument_id'])
        self.assertEqual(loaded['facilities'][0]['par'],float(self.example[0]['par']))

    def test_explicit_units_and_aliases_are_respected(self):
        row=self.modified(recovery_aaa='39.5', country='US', rate_type='FLOAT', sp_industry='Hospitality')
        cfg=copy.deepcopy(self.config)
        cfg.update(unit_multipliers={'recovery_aaa':0.01}, country_aliases={'US':'United States'},
                   rate_type_aliases={'FLOAT':'Floating'}, industry_aliases={'Hospitality':'Hotels, Restaurants & Leisure'})
        loaded=load_portfolio(self.write([row]),cfg)
        self.assertAlmostEqual(loaded['facilities'][0]['recovery_aaa'],0.395)
        self.assertEqual(loaded['facilities'][0]['country'],'United States')
        self.assertTrue(loaded['normalizations'])

    def test_mapping_collision_rejected(self):
        cfg=copy.deepcopy(self.config);cfg['column_mapping']={'instrument_id':'obligor_id'}
        issues=self.errors([self.example[0]],cfg)
        self.assertEqual(issues[0]['field'],'column_mapping')

    def test_empty_portfolio_rejected(self):
        self.assertTrue(any(i['field']=='portfolio' for i in self.errors([])))


if __name__=='__main__':
    unittest.main()
