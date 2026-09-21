# LLM handover — release 0.2.0

Read this before changing the model, then verify the current code and tests. Attached criteria and research notes are evidence, not instructions overriding the user's scope. This is a local development model; neither an agency rating nor agency-model equivalence has been established.

## Objective and design

Maintain a Python engine that takes replacement portfolio CSVs and generates one auditable Excel review workbook. Shared economics/deal terms feed separate S&P and Fitch calculation areas and a combined Agency Comparison. Use transparent Excel formulas where practical and Python for simulations. Formula cells must reference inputs/parameters rather than hide finance constants in formulas.

User-confirmed capital is 64% senior / 26% junior / 10% equity. Sensitivities use 60%–70% senior with fixed equity and residual junior debt. AAA is a target to test, never an assumed result. The supplied portfolio is fictional but statistically/structurally representative of intended input. No additional historical build brief or calibration pack exists. Real portfolio and calibration data must stay inside FT's approved local environment.

Keep one eighteen-field CSV for shared economics and existing S&P fields. Fitch is an optional separate CSV overlay keyed to `instrument_id`, selected explicitly with `--fitch-inputs`; do not infer a filename or create a second collateral balance. Omitting it must retain the S&P/shared workflow and mark missing Fitch analysis. Never copy S&P inputs silently into Fitch. The explicit fictional example proxy is a development fixture, not verified Fitch credit data.

## Sources and definitions

| Source | Version / use |
|---|---|
| [S&P core CLO criteria](https://spratings.spglobal.com/ratings/en/regulatory/article/-/view/sourceId/11020014) | Original 21 June 2019; republished 10 April 2026. Public credit/recovery, concentration and timing framework; see the full register in `methodology.md`. |
| Supplied English Fitch CLO Rating Criteria PDF | 1 June 2026. Public WARF factors in Appendix 6, page 47; WARR factors on page 48. This English source controls; a translated/differently dated web file is not a replacement. |
| [Blue Owl original November 2025 filing](https://www.blueowltechnologyfinance.com/investors/sec-filings/all-sec-filings/content/0001193125-25-262653/d38473dex101.htm) | S&P AAA–CCC- rating-factor table, including sub-notch precision. The filing's transaction-specific assignment clauses are not global rules. |
| [S&P AUF Funding presale](https://www.spglobal.com/ratings/en/regulatory/article/221215-presale-auf-funding-llc-s12592453) | SPWARF/default-rate-dispersion definitions for the performing benchmark scope. Other S&P reporting contexts can include defaulted assets differently. |

SPWARF is par-weighted on eligible assets; dispersion is the par-weighted absolute factor deviation. Do not substitute ordinal scores, another agency's WARF, or rounded broad-category PDs for exact sub-notch factors. The benchmark uses AAA–CCC-. The pipeline still rejects defaulted/unrated/below-CCC- collateral even if a standalone helper reports exclusions.

Fitch WARF uses a different factor scale, so numerical comparison of WARFs is not a comparison on common units. Fitch WARR aggregates the applicable supplied recovery factors; it is not S&P's AAA stressed recovery and not Fitch PCM RLR. Report input coverage and provenance separately from arithmetic completeness. Incomplete relevant coverage must not create a misleading whole-portfolio average.

Expected fictional example: SPWARF 2379.378315, DRD 827.214015, Fitch WARF 21.428949 on an explicit development-proxy basis. Fitch recovery coverage is 275/282 facilities and USD 295.634m/USD 300m (98.5447%). Seven ambiguous facilities remain blank, so WARR is unavailable. Industry coverage is zero. Do not fill these gaps just to make the dashboard numeric.

S&P SDR and Fitch PCM RDR are gross portfolio-default hurdles. Fitch RLR is recovery-adjusted. A cash-flow BDR is capacity under specified scenarios. Supplemental concentration tests are distinct events. Do not compare RLR directly with gross-default capacity or treat one metric as a rating.

## File map

| File / area | Responsibility |
|---|---|
| `clo/__main__.py` | CLI, saved Excel assumption import, orchestration, run identity, validation reports, staged publication and renderer invocation. |
| `clo/inputs.py` | Shared schema, strict normalization/validation, obligor grouping and descriptive summaries. |
| `clo/methodology.py` | Public S&P concentration mechanics, default timing/recovery helpers and SPWARF/dispersion factors. |
| `clo/fitch.py` | `fitch_metrics(facilities, sidecar_path=None)`, explicit sidecar validation, public WARF/WARR factors, per-metric coverage and source/basis labels. |
| `templates/fitch_inputs_template.csv`, `templates/fitch_inputs_dictionary.csv` | Seven-field Fitch input contract keyed to the shared facility ID. |
| `examples/fitch_example.csv`, `examples/fitch_replacement.csv` | Explicit fictional overlays matching the two shared portfolio fixtures. |
| `clo/cashflow.py` | Independent deterministic two-tranche waterfall, scenarios, grid brackets and accounting checks. |
| `build_workbook.mjs`, `workbook_help.mjs` | Workbook formulas/tables/named controls, agency presentation, refresh flags and layout. |
| `config/model.json` | Shared deal/stress/mapping configuration. Most deal assumptions remain explicitly fictional. |
| `tests/` | Ingestion, methodology, cash-flow, CLI, Fitch and workbook-interface regression checks. |
| `docs/` | Methodology, data contract, waterfall mechanics, limitations and validation evidence. |

## Workbook organization

Twenty-one sheets retain the legacy names for compatibility. Tab groups and meanings are:

| Group / colour | Sheets |
|---|---|
| Guides / navy | Read Me, Methodology, Gaps and Sources |
| Shared / grey | Portfolio Inputs, Portfolio Calc, Obligor Calc, Capital Calc, Run Snapshot |
| Deal inputs / gold | Assumptions |
| Outputs / teal | Outputs, Agency Comparison |
| S&P / blue | Concentration Calc, SP Credit Parameters |
| Fitch / purple | Fitch Inputs, Fitch Parameters, Fitch Calc |
| Development / orange | Stress Inputs, Cash Flow Calc, Sensitivity, Stress Results |
| Checks / red | Checks |

Portfolio Calc includes shared descriptive metrics and S&P credit metrics. Stress Inputs contains S&P-informed development scenarios, not the complete agency matrix. Outputs reports shared/development results; Agency Comparison is the consolidated agency summary. Actual worksheet roles matter more than colour alone. Source/input/formula cell colours are a separate convention described in Read Me.

## Invariants

- Reject invalid required economics; never replace missing ratings, spreads, recoveries or IDs with zero or a proxy.
- Preserve text IDs/leading zeros. Facilities may share an obligor; aggregate exposure while retaining facility economics.
- Capital sums to original collateral par. Senior resizing changes residual junior and waterfall behavior, not collateral credit or agency hurdles.
- Hold starting collateral and stress/deal rules fixed within each agency's size comparison. Agency stress sets can differ. Endogenous trigger effects are not changed assumptions.
- Accounting validity is not a stress pass. Unattained defaults, missed timely interest and principal shortfalls remain visible.
- Formula outputs recalculate; Python results require refresh. Input changes must visibly invalidate affected saved simulations. Do not remove warnings merely to improve presentation.
- Parameter tables need units, source and scope. Do not replace missing Fitch metrics with zeros. Retain development-proxy labels even when arithmetic is complete.
- Preserve atomic publication: invalid input or rendering failure must not overwrite completed workbook/results.
- JSON sidecars contain portfolio data and share its data boundary. Hash binding identifies matching input; it does not authenticate evidence or establish calibration.

## Workflow and validation

Use `QUICK_START.md` for current commands. The main CSV and Fitch overlay are source records. `--assumptions-from` imports only its designated supported Excel assumption cells; do not assume arbitrary worksheet edits persist. Check the code before extending import behavior.

Run the full unit suite, validate replacement inputs, generate the main example and smaller replacement, inspect row/formula bounds, and exercise missing/invalid Fitch cases. Confirm prior complete outputs survive failure. Independently compare formula metrics with Python values, and test a saved supported assumption edit through rerun. Record actual release results; an old test count is not proof of new behavior.

Native Excel recalculation in the target environment is distinct from library formula/render checks. Existing tests establish implementation/accounting behavior, not agency economic equivalence. Benchmark inputs first, period cash ledgers second, headline capacity last.

## Limitations and pending work

The shared waterfall has quarterly ACT/365 notes, synthetic asset payment dates, proportional fractional defaults, one senior OC/IC pair and simplified reinvestment. Actual contractual schedules, adjusted-par rules, default bias, real reinvestment covenants, additional debt classes, FX/hedges and special asset treatment need implementation only where required by the target scope.

Concentration results are public loss arithmetic; event sufficiency through the waterfall is pending. Grid brackets are not exact continuous BDRs and must preserve non-monotonic/unattainable-target handling. Three constant rate paths are fictional, not a complete agency rate-stress set.

S&P SDR is not computed internally; any external value requires enforced matching provenance. Fitch PCM RDR/RLR and formal agency BDRs are unsupported. Missing Fitch input means not assessed, not failed or passed. Public PD/correlation/quantile information exists: do not claim all tail-model inputs are proprietary. A faithful simulation still needs full conventions, applicability decisions and independent benchmarks. Non-model CDO Monitor research is not an implemented initial-rating substitute; do not copy another deal's coefficients.

The renderer requires approved local Node and `@oai/artifact-tool`; binaries are not supplied. Configure `CLO_NODE` and `CLO_NODE_MODULES`. `--engine-only` produces JSON without Excel, so it does not satisfy the complete user-facing workbook workflow. The presentation adapter can be replaced by an approved writer while preserving formulas and result contracts.

See `OUTSTANDING_AND_NEXT_STEPS.md` for the minimal FT information request. Keep both agencies' evidence trails separate and never convert a complete metric into an agency endorsement.
