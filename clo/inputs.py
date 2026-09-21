"""Strict, explicit CSV normalization. Units never inferred from magnitudes."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

FIELDS = ['instrument_id','obligor_id','obligor_name','par','sp_rating','sp_industry',
          'country','seniority','rate_type','spread_bps','fixed_coupon_rate','floor_bps',
          'maturity_date','recovery_aaa','price','payment_frequency','currency','benchmark']
CONDITIONAL = {'spread_bps','fixed_coupon_rate','floor_bps','benchmark'}
RATINGS = ['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-',
           'BB+','BB','BB-','B+','B','B-','CCC+','CCC','CCC-','CC','C','SD','D','NR']
NUMERIC = {'par','spread_bps','fixed_coupon_rate','floor_bps','recovery_aaa','price','payment_frequency'}

class ValidationError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__(f"{len(issues)} input error(s); see validation report")

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()

def read_json(path):
    with open(path, encoding='utf-8-sig') as stream:
        return json.load(stream)

def load_portfolio(path, config):
    """Return facilities + row-level normalization log; invalid rows block the run."""
    issues, normalized, facilities, csv_rows = [], [], [], []
    mapping = config.get('column_mapping', {})
    fields = {key: mapping.get(key, key) for key in FIELDS}
    if len(set(fields.values())) != len(fields):
        raise ValidationError([{'row':0,'field':'column_mapping','message':'Two canonical fields map to one incoming column'}])
    def issue(row, field, value, message):
        issues.append({'row':row,'field':field,'value':value,'message':message})
    with open(path, newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        duplicate_headers = [k for k,v in Counter(headers).items() if v > 1]
        for col in duplicate_headers: issue(1,col,col,'Duplicate CSV column header')
        for key, col in fields.items():
            if col not in headers: issue(1,key,None,f'Required column missing: {col}')
        if issues: raise ValidationError(issues)
        for row_no, source in enumerate(reader, start=2):
            if None in source:
                issue(row_no,'CSV',None,'Row has more cells than column headers')
                continue
            raw = {key:source.get(col) for key,col in fields.items()}
            row = {}
            before = len(issues)
            for key in FIELDS:
                value = raw[key]
                if value is None: issue(row_no,key,None,'Row is shorter than the declared schema'); continue
                value = value.strip()
                if raw[key] != value:
                    normalized.append({'row':row_no,'field':key,'from':raw[key],'to':value,'reason':'Trim surrounding whitespace'})
                if not value:
                    if key not in CONDITIONAL: issue(row_no,key,value,'Required value missing')
                    row[key] = None
                    continue
                if key in NUMERIC:
                    try:
                        number = float(value)
                        number *= float(config.get('unit_multipliers',{}).get(key,1))
                        if not math.isfinite(number): raise ValueError()
                        row[key] = number
                    except (ValueError,TypeError): issue(row_no,key,value,'Finite numeric value required; no percent symbols or thousands separators')
                else: row[key] = value
            for key in ['sp_rating','currency']:
                if row.get(key):
                    original = row[key]
                    row[key] = original.upper().replace('−','-')
                    if key == 'sp_rating': row[key] = config.get('rating_aliases',{}).get(row[key],row[key])
                    if row[key] != original: normalized.append({'row':row_no,'field':key,'from':original,'to':row[key],'reason':'Explicit case/rating normalization'})
            for key, aliases_key in [('sp_industry','industry_aliases'),('country','country_aliases'),('rate_type','rate_type_aliases'),('seniority','seniority_aliases')]:
                original = row.get(key)
                row[key] = config.get(aliases_key,{}).get(original, original)
                if row[key] != original: normalized.append({'row':row_no,'field':key,'from':original,'to':row[key],'reason':aliases_key})
            if row.get('sp_rating') not in RATINGS: issue(row_no,'sp_rating',raw['sp_rating'],'Unknown rating symbol; map explicitly to an S&P input')
            elif row['sp_rating'] in ('CC','C','D','SD','NR'): issue(row_no,'sp_rating',row['sp_rating'],'Unrated/defaulted or below CCC- collateral requires a separate approved treatment; unsupported in this prototype')
            for key, allowed in [('sp_industry',config['allowed_industries']),('country',config['allowed_countries']),('seniority',config['allowed_seniorities'])]:
                if row.get(key) not in allowed: issue(row_no,key,raw[key],'Value is outside the configured permitted vocabulary; review mapping')
            if row.get('currency') != config['currency']: issue(row_no,'currency',raw['currency'],'FX and mixed-currency cash flows are not implemented')
            try:
                d = date.fromisoformat(row.get('maturity_date') or '')
                if d.isoformat() != row['maturity_date']: raise ValueError()
                if d <= date.fromisoformat(config['as_of_date']): raise ValueError()
            except ValueError: issue(row_no,'maturity_date',raw['maturity_date'],'Use YYYY-MM-DD, strictly after as-of date')
            for key,low,high,strict in [('par',0,None,True),('recovery_aaa',0,1,False),('price',0,200,True),('spread_bps',0,10000,False),('floor_bps',-1000,10000,False),('fixed_coupon_rate',0,1,False)]:
                v=row.get(key)
                if isinstance(v,(int,float)) and ((v<=low if strict else v<low) or (high is not None and v>high)):
                    issue(row_no,key,raw[key],f'Outside supported range {">" if strict else ">="}{low}, maximum {high}')
            if row.get('payment_frequency') not in (2,4):
                issue(row_no,'payment_frequency',raw['payment_frequency'],'Only semiannual and quarterly-paying assets are supported; no silent frequency conversion')
            if row.get('rate_type') == 'Floating':
                for key in ['spread_bps','floor_bps','benchmark']:
                    if row.get(key) is None: issue(row_no,key,raw[key],'Required for floating-rate asset')
                if row.get('fixed_coupon_rate') is not None: issue(row_no,'fixed_coupon_rate',raw['fixed_coupon_rate'],'Must be blank for Floating asset')
                if row.get('benchmark') != config['benchmark']: issue(row_no,'benchmark',raw['benchmark'],'Benchmark does not match configured rate path')
            elif row.get('rate_type') == 'Fixed':
                if row.get('fixed_coupon_rate') is None: issue(row_no,'fixed_coupon_rate',raw['fixed_coupon_rate'],'Required for fixed-rate asset')
                for key in ['spread_bps','floor_bps']:
                    if row.get(key) is not None: issue(row_no,key,raw[key],'Must be blank for Fixed asset')
                if row.get('benchmark') not in (None,'None','none','N/A'):
                    issue(row_no,'benchmark',raw['benchmark'],'Fixed assets must have blank/None benchmark')
                row['benchmark'] = None
            else: issue(row_no,'rate_type',raw['rate_type'],'Use Floating or Fixed, or configure an explicit alias')
            if len(issues) == before:
                facilities.append(row)
                csv_rows.append(row_no)
    if not facilities and not issues: issue(2,'portfolio',None,'Portfolio must contain at least one facility')
    seen, groups = {}, defaultdict(list)
    for i,row in zip(csv_rows,facilities):
        key=row['instrument_id']
        if key in seen: issue(i,'instrument_id',key,f'Duplicate instrument ID; first occurrence row {seen[key]}')
        else: seen[key]=i
        groups[row['obligor_id']].append(row)
    for oid, group in groups.items():
        for key in ['obligor_name','sp_rating','sp_industry','country']:
            if len({r[key] for r in group})>1:
                issue(0,key,oid,'Conflicting obligor attributes; issuer rating must be consistent across common-default facilities')
    if issues: raise ValidationError(issues)
    return {'facilities':facilities,'normalizations':normalized,'source_hash':sha256(path),'source_rows':len(facilities),'source_name':Path(path).name}

def summarize(facilities, config):
    total = sum(x['par'] for x in facilities)
    by_obligor = defaultdict(list)
    for row in facilities: by_obligor[row['obligor_id']].append(row)
    obligors = []
    for oid, rows in by_obligor.items():
        p = sum(x['par'] for x in rows)
        obligors.append({'obligor_id':oid,'obligor_name':rows[0]['obligor_name'],'sp_rating':rows[0]['sp_rating'],
                         'sp_industry':rows[0]['sp_industry'],'country':rows[0]['country'],'par':p,'facility_count':len(rows),
                         'weight':p/total,'recovery_aaa':sum(x['par']*x['recovery_aaa'] for x in rows)/p})
    obligors.sort(key=lambda x:(-x['par'],x['obligor_id']))
    floating = [r for r in facilities if r['rate_type']=='Floating']
    fpar = sum(r['par'] for r in floating)
    as_of = date.fromisoformat(config['as_of_date'])
    comp = {}
    for key in ['sp_rating','sp_industry','country','seniority','rate_type']:
        rows = defaultdict(float)
        for r in facilities: rows[r[key]] += r['par']
        comp[key] = [{'label':k,'par':v,'weight':v/total} for k,v in sorted(rows.items(),key=lambda x:-x[1])]
    return {'total_par':total,'facility_count':len(facilities),'obligor_count':len(obligors),'obligors':obligors,
            'floating_par':fpar,'weighted_spread_bps':sum(r['par']*r['spread_bps'] for r in floating)/fpar if fpar else None,
            'weighted_recovery':sum(r['par']*r['recovery_aaa'] for r in facilities)/total,
            'weighted_term':sum(r['par']*(date.fromisoformat(r['maturity_date'])-as_of).days/365.25 for r in facilities)/total,
            'weighted_price':sum(r['par']*r['price'] for r in facilities)/total,
            'obligor_hhi':sum(r['weight']**2 for r in obligors),'effective_obligors':1/sum(r['weight']**2 for r in obligors),
            'composition':comp}

def validate_config(config):
    """Validate the full configuration before any economic calculation.

    JSON containers and primitive types are checked before values are consumed.
    Error records are themselves JSON-safe, including rejected NaN/Infinity.
    No missing scalar assumption is replaced by an inferred economic value.
    """
    errors = []
    missing = object()

    def safe(value, depth=0):
        if value is missing:
            return '<missing>'
        if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 1024:
            return '<integer exceeds floating-point range>'
        if value is None or isinstance(value, (str, bool, int)):
            return value[:250] if isinstance(value, str) else value
        if isinstance(value, float):
            return value if math.isfinite(value) else str(value)
        if depth >= 3:
            return '<nested value>'
        if isinstance(value, list):
            return [safe(v, depth + 1) for v in value[:10]]
        if isinstance(value, dict):
            return {str(k)[:100]: safe(v, depth + 1) for k, v in list(value.items())[:10]}
        return '<unsupported ' + type(value).__name__ + '>'

    def err(field, message, value=missing):
        errors.append({'row': 0, 'field': field, 'value': safe(value), 'message': message})

    if not isinstance(config, dict):
        err('configuration', 'Configuration must be a JSON object', config)
        raise ValidationError(errors)

    def numeric(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(value)
        except (OverflowError, ValueError):
            return False

    def number(source, key, low=None, high=None, integer=False, prefix=''):
        value = source.get(key, missing)
        field = prefix + key
        if not numeric(value):
            err(field, 'Explicit finite numeric value required; booleans and numeric strings are not numbers', value)
            return False
        valid = True
        if (low is not None and value < low) or (high is not None and value > high):
            err(field, f'Value must be in [{low}, {high}]', value)
            valid = False
        if integer and value != int(value):
            err(field, 'Integer required', value)
            valid = False
        return valid

    def text_value(source, key, prefix='', required=True):
        value = source.get(key, missing)
        if value is missing and not required:
            return None
        if not isinstance(value, str) or not value.strip():
            err(prefix + key, 'Nonempty text value required', value)
            return None
        return value

    def numeric_array(source, key, low=None, high=None, minimum=1, prefix=''):
        values = source.get(key, missing)
        field = prefix + key
        if not isinstance(values, list) or len(values) < minimum:
            err(field, f'JSON array with at least {minimum} numeric value(s) required', values)
            return None
        valid = True
        for index, value in enumerate(values):
            if not numeric(value) or (low is not None and value < low) or (high is not None and value > high):
                err(f'{field}[{index}]', f'Finite numeric fraction in [{low}, {high}] required; booleans are invalid', value)
                valid = False
        return values if valid else None

    parsed_dates = {}
    for key in ('as_of_date', 'legal_final_date', 'reinvestment_end_date'):
        value = config.get(key, missing)
        try:
            if not isinstance(value, str):
                raise ValueError()
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError()
            parsed_dates[key] = parsed
        except (ValueError, TypeError):
            err(key, 'Exact ISO YYYY-MM-DD calendar date required', value)
    if 'as_of_date' in parsed_dates and 'legal_final_date' in parsed_dates:
        if parsed_dates['legal_final_date'] <= parsed_dates['as_of_date']:
            err('legal_final_date', 'Must be after as-of date', config['legal_final_date'])
    if 'reinvestment_end_date' in parsed_dates:
        reinvest = parsed_dates['reinvestment_end_date']
        if ('as_of_date' in parsed_dates and reinvest < parsed_dates['as_of_date']) or ('legal_final_date' in parsed_dates and reinvest > parsed_dates['legal_final_date']):
            err('reinvestment_end_date', 'Must fall between as-of date and legal final', config['reinvestment_end_date'])

    for key, low, high, integer in (
        ('base_senior_pct', .60, .70, False), ('equity_pct', 0, .4, False),
        ('base_default_rate', 0, 1, False), ('recovery_lag_quarters', 0, 80, True),
        ('starting_cash', 0, 0, False), ('periods_per_year', 4, 4, True),
        ('reinvestment_price', .01, 2, False), ('reinvestment_maturity_years', .25, 30, False),
        ('oc_trigger', 0, 10, False), ('ic_trigger', 0, 10, False),
        ('fixed_fee_per_period', 0, None, False), ('reinvestment_floor_bps', -1000, 10000, False)):
        number(config, key, low, high, integer)
    for key in ('senior_coupon_bps', 'junior_coupon_bps', 'senior_fee_bps', 'subordinated_fee_bps', 'reinvestment_spread_bps'):
        number(config, key, 0, 10000)
    for key in ('annual_prepayment_rate', 'reinvestment_recovery', 'oc_recovery_credit', 'final_liquidation_price'):
        number(config, key, 0, 1)
    for key in ('senior_floor_pct', 'junior_floor_pct'):
        number(config, key, -.1, 1)
    for key in ('principal_support_interest', 'reinvestment_stop_on_trigger'):
        value = config.get(key, missing)
        if not isinstance(value, bool):
            err(key, 'Explicit JSON boolean true or false required', value)
    for key in ('currency', 'benchmark'):
        text_value(config, key)
    currency = config.get('currency')
    if isinstance(currency, str) and (len(currency) != 3 or not currency.isalpha() or currency.upper() != currency):
        err('currency', 'Use a three-letter uppercase currency code', currency)

    vocabularies = {}
    for key in ('allowed_industries', 'allowed_countries', 'allowed_seniorities'):
        values = config.get(key, missing)
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
            err(key, 'Nonempty JSON array of nonempty text values required', values)
        elif len(set(values)) != len(values):
            err(key, 'Permitted vocabulary must contain unique values', values)
        else:
            vocabularies[key] = values

    sizes = numeric_array(config, 'senior_sizes', .60, .70)
    if sizes is not None:
        if sorted(set(sizes)) != sizes:
            err('senior_sizes', 'Use unique ascending sizes', sizes)
        if numeric(config.get('base_senior_pct')) and config['base_senior_pct'] not in sizes:
            err('base_senior_pct', 'Must be one of senior_sizes', config['base_senior_pct'])
        if numeric(config.get('equity_pct')) and any(size + config['equity_pct'] > 1 for size in sizes):
            err('equity_pct', 'Senior plus equity exceeds 100%; residual junior debt would be negative', config['equity_pct'])
    rates = numeric_array(config, 'stress_default_rates', 0, 1, minimum=2)
    if rates is not None and (sorted(set(rates)) != rates or rates[0] != 0 or rates[-1] != 1):
        err('stress_default_rates', 'Unique ascending grid must include 0 and 1', rates)
    numeric_array(config, 'index_rate_path', -.1, 1)

    scenarios = config.get('scenarios', missing)
    ids = []
    if not isinstance(scenarios, list) or not scenarios:
        err('scenarios', 'Nonempty JSON array of scenario objects required', scenarios)
    else:
        for index, scenario in enumerate(scenarios):
            prefix = f'scenarios[{index}].'
            if not isinstance(scenario, dict):
                err(f'scenarios[{index}]', 'Each scenario must be a JSON object', scenario)
                continue
            sid = text_value(scenario, 'id', prefix)
            if sid is not None:
                if any(not (ch.isalnum() or ch in '_-') for ch in sid):
                    err(prefix + 'id', 'Use letters, digits, underscores or hyphens; dots/spaces are unsupported in workbook import keys', sid)
                ids.append(sid)
            text_value(scenario, 'label', prefix, required=False)
            text_value(scenario, 'source', prefix, required=False)
            weights = numeric_array(scenario, 'default_weights', 0, 1, prefix=prefix)
            if weights is not None and abs(sum(weights) - 1) > 1e-9:
                err(prefix + 'default_weights', 'Nonnegative default weights must sum to 1', weights)
            numeric_array(scenario, 'index_rate_path', -.1, 1, prefix=prefix)
            number(scenario, 'recovery_multiplier', 0, 2, prefix=prefix)
            number(scenario, 'annual_prepayment_rate', 0, 1, prefix=prefix)
        if len(set(ids)) != len(ids):
            err('scenarios', 'Duplicate scenario IDs', ids)
    base_id = text_value(config, 'base_scenario_id')
    if base_id is not None and base_id not in ids:
        err('base_scenario_id', 'Must identify a configured scenario', base_id)

    alias_targets = {'rating_aliases': RATINGS,
                     'industry_aliases': vocabularies.get('allowed_industries'),
                     'country_aliases': vocabularies.get('allowed_countries'),
                     'seniority_aliases': vocabularies.get('allowed_seniorities'),
                     'rate_type_aliases': ['Floating', 'Fixed']}
    for key in ('column_mapping', *alias_targets):
        mapping = config.get(key, {})
        if not isinstance(mapping, dict):
            err(key, 'JSON object mapping text keys to text values required', mapping)
            continue
        mapping_valid = True
        for source, target in mapping.items():
            if not isinstance(source, str) or not source.strip() or not isinstance(target, str) or not target.strip():
                err(key, 'Each mapping key and value must be nonempty text', {str(source): target})
                mapping_valid = False
                continue
            if key == 'column_mapping' and source not in FIELDS:
                err(key, 'Column mappings must use canonical field names as keys', source)
                mapping_valid = False
            elif key in alias_targets and alias_targets[key] is not None and target not in alias_targets[key]:
                err(key, 'Alias target is outside the permitted canonical vocabulary', target)
        if key == 'column_mapping' and mapping_valid:
            effective = [mapping.get(field, field) for field in FIELDS]
            if len(set(effective)) != len(effective):
                err(key, 'Two canonical fields map to the same incoming column', mapping)
    multipliers = config.get('unit_multipliers', {})
    if not isinstance(multipliers, dict):
        err('unit_multipliers', 'JSON object of canonical numeric fields and positive multipliers required', multipliers)
    else:
        for field, value in multipliers.items():
            if not isinstance(field, str) or field not in NUMERIC or not numeric(value) or value <= 0:
                err('unit_multipliers', 'Only recognized numeric fields with explicit positive finite numeric multipliers are allowed', {str(field): value})

    if config.get('agency_sdr_aaa') is not None:
        number(config, 'agency_sdr_aaa', 0, 1)
        source = text_value(config, 'agency_sdr_source')
        if source is not None and source.strip().casefold().startswith(('not supplied', 'unavailable', 'unknown', 'tbd')):
            err('agency_sdr_source', 'External SDR requires actual provenance; placeholder text is invalid', source)
        for key in ('agency_sdr_portfolio_hash', 'agency_sdr_credit_hash'):
            portfolio_hash = config.get(key, missing)
            if not isinstance(portfolio_hash, str) or len(portfolio_hash) != 64 or any(c not in '0123456789abcdefABCDEF' for c in portfolio_hash):
                err(key, 'External SDR requires a 64-character hexadecimal SHA-256 binding it to the portfolio and credit inputs', portfolio_hash)
        text_value(config, 'agency_sdr_model_version')
        for key in ('agency_sdr_as_of', 'agency_sdr_criteria_revision'):
            value = config.get(key, missing)
            try:
                if not isinstance(value, str):
                    raise ValueError()
                parsed = date.fromisoformat(value)
                if parsed.isoformat() != value:
                    raise ValueError()
                if key == 'agency_sdr_as_of' and 'as_of_date' in parsed_dates and parsed != parsed_dates['as_of_date']:
                    err(key, 'External SDR as-of date must match the current portfolio as-of date', value)
            except (TypeError, ValueError):
                err(key, 'External SDR requires an exact ISO YYYY-MM-DD date', value)
    if errors:
        raise ValidationError(errors)
    return config
