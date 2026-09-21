# Input provenance and development scope

The prototype starts from the requested S&P methodology and the supplied `Fictional_CLO_Portfolio.xlsx`. The user clarified that no separate build brief, model configuration or internal calibration findings documents exist for this build. They are not treated as missing prerequisites. Development choices must be visible in the configuration and workbook; later testing and refinement using real information belongs within the user's approved local calibration environment.

The user confirmed a base capital stack of 64% senior debt, 26% junior debt and 10% equity. For the requested senior-sizing comparisons, maintain the configured residual allocation policy and disclose it. Portfolio inputs and stress assumptions must remain fixed between comparisons. A target of AAA is a test objective, not an achieved agency rating.

## Supplied fictional portfolio

The original workbook has three sheets: `Overview`, `Portfolio`, and `Data dictionary`. `Portfolio!A1:T283` contains 282 facilities, 270 obligors and USD 300,000,000 par. Eighteen columns are raw inputs; the final two columns calculate weight and remaining term. The delivered CSV preserves the raw data and excludes those two formulas.

The source explicitly describes the records as synthetic development data, with invented borrower labels and instrument identifiers. It also states that aggregate statistics informed generation, sparse relationships were approximated, some industries were assigned fictional labels, and cash-flow/tail-risk equivalence was untested. No underlying private portfolio, issuer keys, calibration targets or supporting calibration tests are embedded. Treat this as supplied unvalidated synthetic data. Do not claim a verified calibration match, agency-equivalent risk or formal anonymity.

| Source attribute | Supplied value or finding |
|---|---|
| Fictional as-of date | 2027-01-01 |
| Par | USD 300,000,000 |
| Facilities / obligors | 282 / 270 |
| Multi-facility groups | 12 obligors, each with two facilities |
| Duplicate facility identifiers | None in the supplied example |
| Conflicting name/rating/industry/country in a group | None in the supplied example |
| Currency | USD on every asset, an explicit fictional assumption |
| Benchmark | SOFR on all 273 floating facilities |
| Floating share | 98.11% of par |
| Fixed share | 1.89% of par across 9 facilities |
| Par-weighted floating spread | 288.469507 bps |
| Par-weighted fixed coupon | 4.097222% |
| Par-weighted fictional stressed recovery | 39.627173% |
| Par-weighted clean price per 100 | 99.432998 |
| Par-weighted contractual remaining term | 5.222635 years |
| Contractual maturity range | 2029-01-15 to 2035-11-30 |
| Rating categories | 10, A− through B−; fictional model inputs |
| Industry labels / risk countries | 54 / 10 |
| Largest grouped obligor | USD 1,224,000, 0.408% of total par |

Independent local aggregation reconciled the source totals and cached summary formulas. This is a consistency check on the tape, not validation of the source's calibration or a credit rating. Fixed assets correctly have blank floating spread, floor and benchmark; floating assets correctly have blank fixed coupon. These are inapplicable fields, not missing mandatory values.

The as-of date is a deliberately fictional future date relative to the build date. It should be retained in the example configuration. The source assumes bullet principal at maturity; remaining term is `(maturity date − as-of date) / 365.25`, not amortising weighted-average life.

The industry labels are explicitly intended for subsequent verified mapping. Mixed terminology and capitalization do not establish a current S&P CDO Evaluator code. The ambiguous `Senior` seniority label does not prove secured status. The provided recoveries may be used as fictional scenario inputs, with that limitation visible; they do not resolve all inputs needed for agency recovery treatment.

## Other supplied reference

The PDF named `Fitch CLO Rating Criteria (06.01.2026) (2).pdf` is Fitch Ratings' **CLOs and Corporate CDOs Rating Criteria**, dated **1 June 2026**, replacing its 21 July 2023 criteria. The title-page date resolves the ambiguous file name. It is a different agency's methodology and is not used as a substitute for S&P default probabilities, correlations, recovery assumptions or rating thresholds.

The subsequently supplied S&P PDF and the requested [S&P source article](https://spratings.spglobal.com/ratings/en/regulatory/article/-/view/sourceId/11020014) are assessed in the separate methodology register. Model outputs must distinguish published criteria, supplied inputs, fictional development assumptions and unavailable proprietary functionality.

## Development assumptions requiring separate labels

The source tape does not provide deal-specific coupons, fees, legal final maturity, coupon payment dates, day counts, default timing, recovery lags, benchmark paths, prepayment, reinvestment rules, OC/IC thresholds or diversion mechanics. The prototype's editable choices for these items are fictional development assumptions unless another identified source explicitly supplies them. No absence is silently replaced by zero. The quoted asset clean prices are descriptive; initial funding and capital sizing use par, and the prototype does not infer a transaction purchase price or implement agency price haircuts from them.

A contractual payment frequency does not specify the first payment date or phase of semiannual payments. The prototype supports frequencies 2 and 4, anchored fictionally to the as-of date. Accrued but unpaid fixed interest is forfeited on default in the development model. These choices are assumptions, not terms supplied by the portfolio. The 64/26/10 capital proportions are user-supplied; a later change to senior sizing must state whether equity stays fixed or is allocated by a residual ratio.

Agency scenario default rates and licensing-dependent model results are different from portfolio statistics and cash-flow break-even default rates. A cash-flow result using fictional recovery and deal assumptions cannot establish an S&P rating. Unsupported criteria tests and proprietary parameter gaps remain visible.

## Included test data

| File | Rows | Obligors | Par | Purpose |
|---|---:|---:|---:|---|
| `examples/example.csv` | 282 | 270 | USD 300,000,000 | Exact raw-field conversion of supplied fictional tape |
| `examples/replacement.csv` | 52 | 50 | USD 55,744,000 | Row-count refresh while preserving all facilities of selected obligors |
| `examples/replacement_large.csv` | 564 | 540 | USD 600,000,000 | Larger mechanical fixture with separately identified copies of all source obligors |
| `examples/invalid.csv` | 6 | 6 | Not a valid portfolio | Deliberate duplicate identifier, missing recovery, invalid rating, invalid date and negative par |

The smaller replacement selects the first fifty obligors in original order and includes all their facilities. No balances are rescaled. The larger fixture uses two full copies with distinct new identifiers and names while keeping raw economic fields unchanged. It tests row-count expansion and grouping, not independent calibration or identical portfolio risk. The six-row invalid fixture changes five fields of the first six example records and is intended to fail validation; its totals are not valid model outputs.

All attachment inspection and CSV preparation were performed locally. Real portfolios and private calibration material should remain in the approved local environment during future testing. Do not submit those inputs to public browsing, hosted examples or external reporting tools as part of this workflow.
