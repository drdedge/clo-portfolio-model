# Portfolio CSV data dictionary

Use UTF-8 CSV with a header row and one row per facility. Dates use `YYYY-MM-DD`. Numbers use a decimal point without currency symbols or thousands separators. Leave an inapplicable conditional field blank; never enter zero to stand for missing information. Text identifiers remain text, including any leading zeroes.

The example files use canonical headers. `examples/column_mapping.json` illustrates the mapping for the human-readable headers in the supplied workbook: each key is a canonical field and its value is the incoming header. Place the mapping under `column_mapping` in the run configuration. Apply that example mapping only to CSV files using those original workbook headers. For the delivered canonical CSV files, retain the canonical mapping in the run configuration.

| Canonical field | Required | Type and unit | Permitted values and meaning |
|---|---|---|---|
| `instrument_id` | Yes | Text | Nonempty, unique facility ID. Reusing the same facility ID is an error even if all other fields agree. |
| `obligor_id` | Yes | Text | Nonempty common-default group ID. Repeat it for different facilities of the same obligor. Never invent a new obligor solely to avoid a duplicate-facility error. |
| `obligor_name` | Yes | Text | Nonempty display name, consistent for a given obligor ID. It is not a grouping key. |
| `par` | Yes | Currency units | Finite positive current drawn principal. The development configuration supports USD. No FX conversion is inferred. |
| `sp_rating` | Yes | Rating category | `AAA`, `AA+`, `AA`, `AA-`, `A+`, `A`, `A-`, `BBB+`, `BBB`, `BBB-`, `BB+`, `BB`, `BB-`, `B+`, `B`, `B-`, `CCC+`, `CCC`, `CCC-`. `CC`, `C`, `D`, `SD` and `NR` are unsupported by this performing-asset cash-flow prototype; unsupported/unknown inputs must be resolved explicitly. The example entries are fictional rating inputs. |
| `sp_industry` | Yes | Text category | A label in the configured permitted list or an explicit configured alias. Original labels are descriptive and have not been verified as S&P CDO Evaluator codes. Unknown labels must be reported for mapping. |
| `country` | Yes | Country-of-risk category | A configured permitted country or alias. The example uses country names. Do not derive risk country from currency or obligor name. |
| `seniority` | Yes | Text category | Source values are `1st Lien`, `Sr Unsec`, `Sr Secured`, `Senior`. The configuration may normalize aliases. `Senior` does not establish secured status; the source's supplied recovery override is fictional. |
| `rate_type` | Yes | Text category | `Floating` or `Fixed`, with configured normalization. |
| `spread_bps` | Floating only | Basis points per annum | Finite floating spread over the benchmark. `250` means 2.50% per annum. Blank for fixed assets. Do not enter `0.025` for 250 bps. |
| `fixed_coupon_rate` | Fixed only | Annual fraction | A finite fraction from 0 to 1. `0.05` means 5% per annum. Blank for floating assets. |
| `floor_bps` | Floating only | Basis points | Finite benchmark floor. `50` means a 0.50% floor on the benchmark before adding spread. Zero is a real, explicit floor. Blank for fixed assets. |
| `maturity_date` | Yes | ISO calendar date | Valid `YYYY-MM-DD`, after the configured as-of date. The example assumes bullet repayment. Contractual maturity is not amortising weighted-average life. |
| `recovery_aaa` | Yes | Fraction | Finite recovery fraction from 0 to 1. `0.40` means 40% of defaulted principal. The example contains supplied fictional stressed recovery inputs; the field name does not establish agency approval. |
| `price` | Yes | Clean price per 100 par | Finite positive price up to 200. `99.5` means 99.5% of par. Above-par prices are allowed. Price is descriptive in this prototype; funding and capital sizing use original par, not market value. Price does not implement agency discount-asset or CCC haircuts. |
| `payment_frequency` | Yes | Integer payments/year | `2` or `4`. The source uses `4` for floating and `2` for fixed instruments. Other frequencies are rejected. Coupon dates use a fictional anchor at the configured as-of date; this is not supplied contractual payment-date evidence. |
| `currency` | Yes | Currency code | `USD` for the delivered configuration. Other currencies require supported treatment; no silent conversion. |
| `benchmark` | Floating only | Benchmark name | `SOFR` in the delivered configuration, or an explicitly supported configured benchmark. Blank for fixed assets. |

Conditional fields are optional when their rate type makes them inapplicable, but all eighteen column headers are required. Blank values must not be automatically converted to economic zero. Additional identifiers or provenance columns may be kept in a user's source file, but they do not affect calculations unless explicitly supported and mapped by the engine. Extra fields remain in the original source CSV, identified by its recorded file hash, and are not exported to the normalized facility table. Do not rely on extra columns to change model behavior.

## Portfolio and obligor validation

The engine must distinguish facility uniqueness from obligor grouping. It aggregates facility par under a shared `obligor_id` for concentration measures and common-default analysis. Facility coupons, recovery inputs and maturities remain separate. Conflicting obligor-level names, ratings, industries or countries require review; they must not be averaged or resolved by taking whichever row appears first.

Normalize harmless representation differences such as surrounding whitespace, recognized rating-minus characters and explicit configured category aliases. Do not infer unknown ratings, recovery values, industries, units or currencies. Invalid required data should produce a field-level diagnostic identifying the CSV row and prevent generation of a successful calculation workbook.

Derived portfolio weight and remaining term are recomputed from raw par, dates and the configured as-of date. The source workbook's `Weight` and `Remaining term years` columns are excluded from the CSV. Formula text is not an acceptable numeric input.

## Supplied source header mapping

| Canonical field | Original workbook header |
|---|---|
| `instrument_id` | Instrument ID |
| `obligor_id` | Obligor ID |
| `obligor_name` | Obligor name |
| `par` | Par USD |
| `sp_rating` | S&P rating input |
| `sp_industry` | S&P industry |
| `country` | Country |
| `seniority` | Seniority |
| `rate_type` | Rate type |
| `spread_bps` | Spread bps |
| `fixed_coupon_rate` | Fixed coupon |
| `floor_bps` | Floor bps |
| `maturity_date` | Maturity |
| `recovery_aaa` | AAA recovery input |
| `price` | Price |
| `payment_frequency` | Payments per year |
| `currency` | Currency |
| `benchmark` | Benchmark |

## Refresh examples

- `examples/example.csv`: supplied fictional portfolio converted without changing the eighteen raw input fields, with dates serialized as ISO text.
- `examples/replacement.csv`: every facility of the first fifty obligors in source order. This yields fifty-two rows and preserves the two facilities of each repeated obligor included in the subset. Par is not rescaled.
- `examples/replacement_large.csv`: two copies of the full example, with distinct fictional instrument/obligor identifiers and names for each copy. This yields 564 facilities, 540 obligors and USD 600 million par. It tests a larger input and retains all within-copy facility grouping. It is a mechanical test fixture, not an independently calibrated portfolio.
- `examples/invalid.csv`: six rows with deliberate errors. CSV line 3 repeats the facility ID from line 2; line 4 omits recovery; line 5 contains an invalid rating; line 6 contains the impossible date `2032-02-30`; line 7 has negative par. This file should be rejected, with more than one error reported where available.

The replacement portfolio tests changing row count and grouping. It is a selected subset, not a newly calibrated portfolio or a diversification-equivalent substitute.
