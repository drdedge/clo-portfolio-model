# Methodology basis and implementation boundary — release 0.2.0

This is a reusable development model with shared portfolio/deal inputs, separate S&P and Fitch public calculations, and an independent cash-flow engine. It implements S&P SPWARF/dispersion and concentration arithmetic, plus Fitch WARF/WARR where the separate inputs are complete. It does not reproduce CDO Evaluator, Cash Flow Evaluator, CDO Monitor or Fitch Portfolio Credit Model (PCM). Neither agency's AAA outcome is determined. The shared development waterfall is not a full Fitch or S&P cash-flow implementation.

## Version confirmation

Research and version checks were completed on **21 September 2026**.

The controlling source is **Global Methodology And Assumptions For CLOs And Corporate CDOs**, originally published **21 June 2019**, **republished 10 April 2026**, article **3547721**. Both the user's 66-page PDF and the live [S&P criteria page](https://www.spglobal.com/ratings/en/regulatory/article/-/view/sourceId/11020014) show this revision. The original date remains in the page heading and PDF footer; it is not the latest revision date. The [S&P in-use CDO criteria index](https://www.spglobal.com/ratings/en/regulatory/ratings-criteria/-/articles/criteria/structured-finance/filter/cdos) identifies this as the applicable corporate CLO criteria.

The supplied PDF is `547ac06e-3274-450f-a495-3909a41d1a23.pdf`; SHA-256 is `e015300f265c5b46f091e9895030f5f24bd3a89a3f00821504471e0fddc16bb3`. The package does not redistribute the copyrighted criteria PDF.

Relevant changes in the current source are:

| Revision | What matters for this build |
|---|---|
| 10 April 2026 | Country recovery grouping changed for India from C to B; Malaysia assigned B. Do not use older country tables without checking this revision. |
| 1 December 2025 | Clarified distressed exchanges/current-pay treatment in paragraphs 215-217 and 221-224. This prototype rejects defaulted/unrated exposure rather than improvising that treatment. |
| 27 June 2025 | Updated industry/correlation tables for project finance assets. Project finance is outside this build's implemented corporate scope. |
| 25 October 2024 | Moved guidance into Appendices E and F, without substantive change. The separately published 2019 guidance is archived and is not the controlling current source. |

The separate Fitch source is the user-supplied **English** `Fitch CLO Rating Criteria (06.01.2026) (2).pdf`, titled **CLOs and Corporate CDOs Rating Criteria** and dated **1 June 2026** on its first page. Its SHA-256 is `bc5ba4596e244bf87a12a02b6412d7e2adec3d8c484baa6c4bbb1b05f4f1b548`. The implemented public factors are in Appendix 6, pages 47–48; rating equivalency and recovery classification need Appendix 5 and Appendix 4 respectively. The supplied English PDF controls this implementation; a differently dated or translated web document is not a replacement source. Fitch parameters are not used to calibrate S&P calculations.

The user clarified that separate build-brief, configuration, and internal-calibration documents do not exist. The configuration is therefore a documented development specification derived from the request and public criteria, with invented deal terms labelled accordingly. The example portfolio is supplied fictional data; its schema/statistical similarity does not validate ratings, recovery assumptions or calibration. Copyrighted source PDFs are not redistributed in the package.

## Related criteria register

| Source | Version verified | Role and implementation |
|---|---|---|
| [Global Framework For Payment Structure And Cash Flow Analysis Of Structured Finance Securities](https://www.spglobal.com/ratings/en/regulatory/article/-/view/sourceId/11734324) | Original 22 December 2020; republished 17 November 2025, confirmed on live page | Companion framework for payment promises, liquidity and waterfall analysis. This independent engine models stated development terms; it is not certified as a full implementation. |
| [Methodology For Determining Ratings-Based Inputs](https://www.spglobal.com/ratings/pt/regulatory/article/-/view/sourceId/13109302) | Original 26 July 2024; republished 3 October 2025 | Relevant to ratings accepted into credit analysis. Supplied normalized rating inputs remain user attestations; the model does not manufacture S&P credit estimates or approve another CRA's ratings. |
| [Methodology To Derive Stressed Interest Rates In Structured Finance](https://spratings.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3556620) | Original 18 October 2019; republished 5 May 2026 | Defines S&P interest-rate stress approach. The delivered editable development paths are not S&P's CIR curves. Approved curves must be obtained, dated and integrated for agency-aligned calibration. |
| [Counterparty Risk Methodology](https://www.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3412992) | 25 July 2025 | Account bank, hedge and other counterparty exposure review is outside the numerical prototype. It can constrain a rating even when cash flows pass. |
| [Asset Isolation And Special-Purpose Entity Methodology](https://www.spglobal.com/ratings/ru/regulatory/article/-/view/sourceId/13431320) | 29 May 2025 | Non-U.S. legal criteria; relevant legal regimes and U.S. companion criteria require counsel/deal review. No legal conclusion is generated. |
| [Recovery Rating Criteria For Corporate Issuers](https://www.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3538849) | Current in-use publication 31 March 2026 | Source of corporate recovery opinions, which are inputs to CLO recovery analysis. This model does not assign recovery ratings. |
| [Methodology For Rating Structured Finance Securities Above The Sovereign](https://www.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3545165) | Current in-use publication 10 April 2026 | Current sovereign-related criteria. Country-specific ceilings/stresses are outside the prototype. |

The related register identifies dependencies, not a claim that every related framework is automated. Applicability also depends on jurisdiction, asset type, legal documents, manager, hedges and counterparties. The operational-risk framework, FX criteria and recovery-jurisdiction assessments remain deal-review dependencies. Mixed-currency portfolios are blocked in this version. See the current [S&P structured-finance criteria index](https://www.spglobal.com/ratings/en/regulatory/ratings-criteria/-/articles/criteria/structured-finance/filter/all) before promoting a local calibration to production.

## Four different analytical layers

1. **Portfolio credit analysis** describes obligors, credit quality, exposures, industries, geography, tenor and recoveries. Facility balances aggregate to the same obligor before concentration and common-default analysis. Ratings and recovery rates have distinct purposes. Spread, weighted maturity, rating mix, HHI and effective obligor count are descriptive measures; none is an agency rating or SDR.
2. **SDR** is the portfolio default threshold associated with a rating stress in CDO Evaluator. It depends on the portfolio, ratings, tenor, correlations, calibration and quantiles. It is not the mean loss, expected default rate, a credit-enhancement percentage or a user-selected stress severity. For a fixed portfolio and common target stress, it must not change just because senior debt is resized.
3. **Cash-flow BDR** is the maximum gross default rate the specified tranche can withstand under a cash-flow scenario while meeting its applicable interest and principal promises. In the agency framework, the minimum across required scenarios is compared with the corresponding SDR. This build reports independent **fixed-grid first-failure brackets**, with infeasible-default and non-monotonic cases identified. It does not determine an exact maximum, an agency BDR, or an SDR-to-BDR rating conclusion.
4. **Supplemental concentration tests** are separate event-risk stresses. The implementation computes their public default and loss amounts. It does not declare tranche sufficiency from loss arithmetic or subordination alone; where excess spread is used, paragraph 56 calls for payment/cash-flow assessment.

These distinctions follow paragraphs 8-18 and 44-66 of the controlling source. Passing one layer does not establish the others. Analyst judgment, legal, operational, counterparty and sovereign risks can also constrain a rating.

## S&P public components implemented

`clo/methodology.py` contains no external calls and records source metadata. Concentration/timing/recovery references come from the supplied criteria. SPWARF uses the separately verified public sources below.

### SPWARF and default-rate dispersion

`SPWARF = sum(par × rating factor) / eligible par`. `DRD = sum(par × abs(rating factor − SPWARF)) / eligible par`. Both Python and Excel calculate these metrics; **SP Credit Parameters** exposes the nineteen factors rather than embedding them in cell formulas.

The precise AAA–CCC- scale is verified from the S&P Rating Factor table on printed page 61 of [Blue Owl Technology Finance's original November 2025 legal filing](https://www.blueowltechnologyfinance.com/investors/sec-filings/all-sec-filings/content/0001193125-25-262653/d38473dex101.htm). For example, B is 2859.50 and CCC- is 5751.10. Its deal-specific rating-assignment clauses are not imported. Definitions and performing-population scope are supported by table 13 footnotes in [S&P's AUF Funding presale](https://www.spglobal.com/ratings/en/regulatory/article/221215-presale-auf-funding-llc-s12592453).

The benchmark includes assets rated CCC- or higher. A helper reconciles excluded par and returns no metric when eligible par is zero; the end-to-end cash-flow ingestion still rejects unrated/defaulted/below-CCC- collateral. Other S&P reporting conventions can include defaulted assets, so the scope label is material. No ordinal rating score or another agency's WARF is substituted. For the fictional example, SPWARF is 2379.378315 and DRD 827.214015. Neither metric is an AAA SDR or tranche default probability.

### Largest obligor default test

The model first sums all facilities of each obligor. It applies every relevant row of table 4 to the rating band and takes the highest net loss. For AAA, the bands and counts are:

| Eligible obligor ratings | Largest obligors assumed to default |
|---|---:|
| AAA through CCC- | 2 |
| AA+ through CCC- | 3 |
| A+ through CCC- | 4 |
| BBB+ through CCC- | 6 |
| BB+ through CCC- | 8 |
| B+ through CCC- | 10 |
| CCC+ through CCC- | 12 |

Each row is a separate scenario; the rows are not added together. An insufficient number of eligible obligors means selecting all available eligible obligors. The corporate flat recovery is **5%**, so each scenario's net loss is selected par multiplied by **95%**. The module also supports the published AA, A, BBB, BB, B and CCC liability-category columns; plus/minus modifiers share their category's concentration test. See table 4 and paragraphs 123 and 157-161.

The result includes eligible count, selected count, selected obligor IDs, rating band, gross default amount, gross default rate, recovery rate, net loss amount and net loss rate. Conflicting ratings/industries within an obligor block calculation. Corporate exposures below CCC- are rejected: paragraph 161 requires a separate defaulted-asset valuation treatment, which is not implemented. Sovereign exceptions are not implemented.

### Largest industry tests

These apply to AAA and AA-category targets. The primary test defaults the whole largest industry using **17%** recovery. Its loss is industry par multiplied by **83%**. The alternative applies the published rating-band counts separately within each industry, using **5%** recovery, and takes the highest loss across all eligible industry/band scenarios.

For AAA, alternative counts corresponding to the seven bands above are **4, 6, 8, 12, 16, 20, 24**. For AA they are **2, 4, 6, 8, 12, 16, 20**. The primary and alternative industry routes are **alternatives**: the criteria allow the alternative when the primary does not pass. The module reports both without treating their maximum as a mandatory combined stress. Both remain separate from the largest-obligor test. See paragraphs 59-65 and 162-164.

The input industry's correctness matters. Text normalization or a configuration alias does not establish that a supplied industry is the applicable S&P CDO Evaluator classification. The table 18 classification reference must be reviewed in the approved calibration environment.

### Published default timing

Table 20 annual shares of cumulative defaults are **39/22/16/13/10**, **16/23/26/22/13**, **12/18/22/23/25**, and **20/20/20/20/20**. They sum to 100% and do not set the cumulative default rate. Paragraph 133 describes their usual application to leveraged-loan portfolios with weighted-average maturity of four to seven years. Table 21's three-year vectors are also available in the helper. Annual amounts must be spread over payment periods, and defaulted assets produce no interest in the default period (paragraph 132). Different tenors and pro-rata structures need further work.

### Public recovery lookup helper

The optional `public_asset_type_recovery` helper reproduces table 15 for corporate first-lien non-covenant-lite loans, covenant-lite loans/senior-secured bonds, second-lien/unsecured assets and subordinated assets, across explicit recovery country groups A/B/C and liability categories.

It is not used to overwrite portfolio inputs. Recovery-rating information and senior-asset recovery ratings can take precedence under paragraphs 112-114 and tables 12-14. Accurate use also needs covenant-lite status, lien/payment priority and country group. The example's `recovery_aaa` is a supplied fictional scenario assumption, not automatically an S&P-calibrated value. A first-lien label alone does not resolve covenant-lite treatment. Country groups must include the April 2026 changes.

## Fitch public components implemented

`clo/fitch.py` reads an optional, explicitly selected `--fitch-inputs` CSV. Its seven fields are defined in `templates/fitch_inputs_dictionary.csv`; `instrument_id` joins to the shared portfolio. No filename, Fitch rating, recovery or industry mapping is inferred from S&P data. Duplicate/unmatched IDs, invalid values and conflicting issuer-level inputs fail validation. Missing optional Fitch content instead produces disclosed coverage gaps.

**WARF:** the par-weighted Appendix 6 rating factor. This factor is numerically the ten-year PCM asset default rate expressed in percent; for example B is 23.671. It is a different scale/horizon from S&P's factor scale. A row requires a Fitch rating/equivalency, explicit input basis and source reference. The model does not approve Appendix 5 equivalency merely because a user selects that basis.

**WARR:** the par-weighted applicable recovery fraction. Issue recovery estimates or rating-derived factors take precedence where available; the Appendix 6 BBsf fallback requires the appropriate reviewed classification. This is not the portfolio's supplied `recovery_aaa` and is not Fitch PCM's rating loss rate. The reference recovery table is visible on **Fitch Parameters**; classification and asset-level assignment remain explicit inputs.

WARF and WARR each require **100% coverage of their own required fields** before a whole-portfolio number is reported. Otherwise Python returns `None` and Excel displays the missing-input state; it does not publish a partial-subset mean as a full-portfolio result. Industry coverage is separate: populated labels still require review against Fitch's taxonomy, and no Fitch concentration test is implemented. Arithmetic completeness never establishes rating-source validity or a completed Fitch analysis.

The fictional example's ratings are all labelled `development_proxy`, explicitly copied from the supplied fictional S&P inputs. Its WARF is 21.428949 with development-assumption status. Recovery assumptions cover 275 first-lien facilities, USD 295.634 million of USD 300 million (**98.5447%**), using explicit assumed senior-secured-loan/Strong classifications and Group 1/2 75%/65% factors. Seven ambiguously classified facilities remain blank; whole-portfolio WARR is unavailable. Industry coverage is **0%**. These are auditable development choices, not agency recovery opinions or a production classification mapping.

Fitch PCM RDR, RRR and RLR, Fitch stress/waterfall sufficiency, full concentration treatment and an AAA result remain unsupported. The comparison sheet keeps these outputs distinct from S&P SDR and the independent development cash flows. RLR is recovery-adjusted and must not be compared directly with a gross-default capacity.

## What remains unavailable or approximate

| Item | Treatment in this package | Work needed in the approved environment |
|---|---|---|
| CDO Evaluator SDR | Not computed; an external AAA value requires enforced source/version, date/revision and raw/normalized input bindings | Obtain authorized evaluator output or an independently validated implementation and calibration. Independently verify the evidence; matching metadata does not certify agency equivalence. |
| Public default/correlation/quantile tables | Recognized as available in main criteria; not enough to claim exact model reproduction | Validate refined rating transition treatment, interpolations, asset taxonomy, pairwise overrides, multiple maturities per obligor, simulation conventions and calibration against trusted outputs. |
| S&P rating assignment and metric applicability | SPWARF/DRD are implemented from verified public factors; supplied rating assignments remain input attestations | Review the applicable rating hierarchy and population scope. No missing factor table is being assumed. |
| Fitch complete input coverage | Separate public WARF/WARR calculations; example WARR and industry mapping incomplete | Supply reviewed Fitch rating/recovery/classification inputs and provenance. Do not silently reuse S&P input fields. |
| Fitch PCM and cash-flow analysis | RDR/RRR/RLR and agency BDR/AAA result are not calculated | Obtain matching authorized model outputs or independently benchmarked implementation; implement applicable Fitch stresses and deal waterfall. |
| CDO Monitor non-model formula | Not reproduced | Obtain approved coefficients and transaction-specific settings. Public descriptive benchmark formulas are not the full Monitor test. |
| Rate paths | Editable fictional development assumptions | Import correct current S&P stress curves and forward curve for benchmark/currency/target, then validate interpolation and timing. |
| Recovery and recovery lag | Supplied scenario recovery and editable development timing | Resolve applicable S&P recovery hierarchy and deal-specific timing; validate against evaluator/cash-flow calibration. |
| Reinvestment and OC/IC mechanics | Explicit simplified development rules | Reconcile each numerator adjustment, denominator, trigger, cure priority and reinvestment condition against actual deal documents. |
| Portfolio amortization | Independent development schedule | Compare actual/static schedules or the applicable standardized profile with Appendix E paragraphs 128-131 and table 19. |
| Supplemental sufficiency | Public loss arithmetic only | Apply event scenarios to the approved waterfall, including interest timing and ultimate principal. |
| Agency rating conclusions | Not generated for either agency | Require the full applicable analysis and the relevant agency's rating process. |

The public main criteria include asset default rates without modifiers (table 3 and Appendix B), correlation assumptions and overrides (Appendix C), and rating quantiles (Appendix D). Their availability must not be misrepresented as absence of public parameters. Conversely, reading those tables does not establish an exact reproduction of S&P's stochastic implementation. The prototype intentionally leaves agency SDR and rating results unavailable rather than renaming an exploratory percentile as an S&P result.

The [S&P CDO Monitor update](https://www.spglobal.com/ratings/en/regulatory/article/-/view/sourceId/11037205) and [How To Build Your Own CDO Monitor E8](https://www.spglobal.com/ratings/en/regulatory/article/-/view/sourceId/11039942) have restricted public access. SPWARF's factor table is now verified separately; complete Monitor applicability/metric definitions and transaction-specific BDR coefficients remain a distinct dependency. Non-model Monitor is not delivered as a substitute for initial-rating simulation. The actual portfolio development approach also does not imply S&P's **stable quality** treatment, which depends on documented maintenance/reinvestment commitments. Without those protections, the criteria's **stressed portfolio** approach uses covenanted boundaries (paragraphs 68-71 and 99-101).

## Capital-structure comparisons and review rules

The user confirmed a **64% senior / 26% junior / 10% equity** base stack and senior sensitivity range **60%-70%**. Equity stays at the selected 10% and junior debt is the residual, so the sensitivity stacks sum to 100%. Coupons, fees, triggers and other deal timing are labelled fictional development assumptions. Every comparison uses the same collateral input snapshot, recovery assumptions and stress set. Resizing the senior updates residual capital and the waterfall; it does not improve the input collateral or relax the stress. Reinvestment differences caused by identical coverage rules are endogenous scenario outcomes.

Treat a shortfall-free run as survival of the named development scenario. Grid brackets describe tested points and do not establish an exact default capacity. A raw event-loss amount does not establish cash-flow sufficiency. None of these alone establishes an AAA rating. Workbook checks identify stale Python results after edits, input errors, conservation failures and unsupported scope. Recalculation/refresh instructions are in the operating guide; the exact engine mechanics are in `cashflow_design.md` and the delivery/calibration plan is in `build_plan.md`.

## Calibration handoff

The package is designed to be taken into the user's approved local environment. Before real-data validation, inventory authorized agency outputs, rating/recovery evidence, agency-specific industry/country mappings, current stress curves and transaction documents. Compare normalized portfolio totals and issuer grouping first; then credit metrics, event stresses and cash flows separately. Keep the shared collateral/economics fixed; apply each agency's applicable inputs/stresses separately and hold those fixed across its sizing comparisons. Preserve source files and regression fixtures. See `OUTSTANDING_AND_NEXT_STEPS.md` and `LLM_HANDOVER.md`. No real portfolio data was needed or transmitted during this build.
