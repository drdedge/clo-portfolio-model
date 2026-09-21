# CLO portfolio review model — release 0.2.0

One local Python process produces a formula-driven Excel workbook with shared portfolio/deal inputs, separate S&P and Fitch credit calculations, combined agency results, exploratory cash flows and validation checks. Replacement portfolios can change row count without editing formulas or code.

This is a transparent development and calibration tool. It does not assign ratings or reproduce either agency's complete model. S&P SDR is not generated internally; Fitch PCM RDR/RLR and formal agency BDRs are unsupported. Missing Fitch data remains visible as not assessed.

## Start here

1. Open `examples/Example_CLO.xlsx`: read **Read Me**, then **Agency Comparison**, then inspect **Portfolio Inputs**, **Fitch Inputs** and **Assumptions**.
2. Follow [QUICK_START.md](QUICK_START.md) to replace inputs, regenerate and interpret checks.
3. Read [Outstanding work](docs/OUTSTANDING_AND_NEXT_STEPS.md) before calibration. A future developer/assistant should start with [LLM handover](docs/LLM_HANDOVER.md).

The supplied fictional example contains 282 facilities, 270 obligors and USD 300 million par. The user-confirmed stack is 64% senior / 26% junior debt / 10% equity. Senior sensitivities span 60%–70%, with fixed equity and residual junior debt. The same starting collateral and configured stress/deal rules apply across sizes.

## Generate a workbook

From the package directory, use the existing shared portfolio CSV and an explicitly selected Fitch overlay:

```powershell
python -m clo --portfolio examples/example.csv --fitch-inputs examples/fitch_example.csv --config config/model.json --output Example_CLO.xlsx
```

For the replacement demonstration:

```powershell
python -m clo --portfolio examples/replacement.csv --fitch-inputs examples/fitch_replacement.csv --config config/model.json --output Replacement_CLO.xlsx
```

The overlay is optional. This command retains the shared/S&P workflow and shows Fitch's missing-input status:

```powershell
python -m clo --portfolio examples/replacement.csv --config config/model.json --output Shared_SP_Review.xlsx
```

No Fitch filename is inferred. Select the matching overlay each run. The outputs are the workbook, `*.results.json` and `*.validation.json`. Failed required input checks stop publication and preserve prior completed outputs. JSON contains portfolio information and belongs in the same approved environment as the source files.

To validate without running simulations/rendering, add `--validate-only`. To calculate JSON without Excel, add `--engine-only`; that mode is not the full workbook deliverable.

## Input contracts

The shared CSV keeps the original eighteen-column contract in [the data dictionary](docs/data_dictionary.md). Start from `templates/portfolio_template.csv`. One row is one facility; repeated `obligor_id` groups the same default entity. Preserve text IDs, including leading zeros. Use full currency units for par, basis points for spreads/floors, decimal fractions for fixed coupons/recoveries, price per 100, and ISO dates.

All standard headers are required; fields may be blank only where their documented conditional treatment permits it. The current engine supports performing corporate assets rated AAA–CCC-, one currency/benchmark, quarterly notes and quarterly/semiannual assets. Unsupported types or missing economics fail validation. Extra CSV columns do not affect calculations unless explicitly supported.

Column names, explicit unit multipliers and recognized aliases belong in `config/model.json`. For example, `column_mapping` can map `instrument_id` to `Loan ID`. Never infer scale or turn unknown categories into an unreviewed “Other”. See `examples/column_mapping.json` for the supplied workbook's headers.

Fitch uses `templates/fitch_inputs_template.csv` and [its dictionary](templates/fitch_inputs_dictionary.csv):

| Field | Meaning |
|---|---|
| `instrument_id` | Exact shared facility ID; no duplicate/unmatched identifiers. |
| `fitch_idr` | Fitch IDR or explicitly reviewed/development equivalent. |
| `fitch_rating_basis` | `public_fitch_idr`, `reviewed_appendix5_equivalent` or `development_proxy`. |
| `fitch_industry` | Applicable Fitch classification; blank means unresolved, not inherited from S&P. |
| `fitch_recovery` | Applicable WARR recovery factor as a fraction; not S&P's AAA stressed recovery. |
| `fitch_recovery_basis` | `fitch_issue_recovery_estimate`, `fitch_issue_recovery_rating`, `reviewed_bbsf_fallback` or `development_assumption`. |
| `source_reference` | Reviewable rating/recovery source or explicit development-assumption explanation. |

Incomplete Fitch economics can leave supported metrics unassessed while preserving other analysis. Duplicate/unmatched IDs and malformed values are structural errors. WARF and WARR coverage are assessed separately: do not present a partial-subset mean as the full portfolio's metric.

The example Fitch ratings deliberately use the fictional S&P ratings as labelled development proxies. Recovery assumptions cover 275 of 282 facilities, USD 295.634 million of USD 300 million (98.5447%); seven ambiguously classified assets remain blank. Fitch industry coverage is 0%. Example WARF is 21.428949 on the development proxy basis; whole-portfolio WARR remains unavailable. These are calculation demonstrations, not independently sourced Fitch credit opinions.

## Workbook map

The 21 sheets retain the original sheet names for compatibility. Use their page titles and explanatory notes as well as tab colours.

| Group | Sheets / purpose |
|---|---|
| Guides / navy | Read Me, Methodology, Gaps and Sources. |
| Shared / grey | Portfolio Inputs, Portfolio Calc, Obligor Calc, Capital Calc, Run Snapshot. Portfolio Calc includes shared descriptive measures and S&P SPWARF/dispersion. |
| Deal inputs / gold | Assumptions. |
| Combined outputs / teal | Agency Comparison is the side-by-side agency summary; Outputs presents shared portfolio and development cash-flow results. |
| S&P / blue | SP Credit Parameters exposes factors; Concentration Calc contains public event-loss arithmetic. |
| Fitch / purple | Fitch Inputs, Fitch Parameters and Fitch Calc expose the separate overlay, sourced parameters and supported public metric formulas. |
| Development / orange | Stress Inputs, Cash Flow Calc, Sensitivity and Stress Results. Timing is S&P-informed; these are not complete Fitch or S&P stress/cash-flow models. |
| Validation / red | Checks. Resolve errors/stale results and inspect Gaps and Sources before interpreting output. |

Cell colours have separate meanings from tab colours: imported/source/Python values use grey fill; editable assumption cells use blue text with amber fill; within-sheet formulas are black and cross-sheet formulas green. Parameter constants are sourced reference values rather than user inputs; no worksheet-protection guarantee is made.

## Excel changes and refresh

Portfolio and supported agency metrics use visible formulas where practical. Simulations, stress-grid results and selected concentration exposures come from Python. Changing relevant inputs shows **REFRESH REQUIRED** for affected saved results; Excel does not run Python automatically. Keep Excel calculation automatic.

Save supported edits on **Assumptions** and **Stress Inputs**, then rerun:

```powershell
python -m clo --portfolio examples/example.csv --fitch-inputs examples/fitch_example.csv --config config/model.json --assumptions-from Edited_CLO.xlsx --output Refreshed_CLO.xlsx
```

Only designated literal assumption/rate cells are imported. Formulas in editable imported cells are rejected. The shared CSV remains portfolio authority; Fitch edits must be saved to the Fitch CSV. Editing **Fitch Inputs** directly may recalculate visible formulas and flag refresh, but those edits are not imported by `--assumptions-from`. Sourced parameter tables are not an override interface; parameter edits require reviewed source/code updates and rerunning. Checks detect discrepancies with expected parameters.

Edit JSON for mappings, scenario membership/identity, structural arrays and vocabulary lists. Scenario-level prepayment overrides the global fallback; changing only the fallback does not change a scenario with its own value. Reinvestment is disabled in the base configuration and can be enabled through its documented development controls.

## Methodology boundaries

S&P's pinned source is the 21 June 2019 criteria republished 10 April 2026. SPWARF uses the performing benchmark scope and a verified public factor table; dispersion uses par-weighted absolute factor deviation. Public largest-obligor/industry event-loss calculations are implemented, but their waterfall sufficiency is not. An external AAA SDR requires matching source/version/date and input hashes; metadata does not authenticate the supplied result.

Fitch's controlling source is the supplied English criteria PDF dated 1 June 2026. Public WARF/WARR formulas and parameters do not reproduce PCM default/loss distributions. Agency WARFs have different scales, and Fitch WARR is not interchangeable with S&P AAA stressed recovery. The combined page preserves those differences and reports unsupported results explicitly.

The independent waterfall uses fictional deal assumptions, four public S&P timing patterns crossed with three fictional flat rate paths, and a default-severity grid. It reports last tested pass/first tested failure intervals, with unattainable and non-monotonic cases identified. It does not establish a continuous maximum BDR or either agency's AAA result. See [methodology](docs/methodology.md), [cash-flow design](docs/cashflow_design.md) and [outstanding work](docs/OUTSTANDING_AND_NEXT_STEPS.md).

## Runtime and local deployment

Use Python 3.10+; reading saved Excel assumptions requires `openpyxl` from `requirements.txt`. The engine otherwise uses standard-library processing. Excel generation additionally requires an approved local Node runtime and `@oai/artifact-tool`. Runtime binaries are not bundled in the delivery ZIP.

If bundled paths differ, set `CLO_NODE` to the Node executable and `CLO_NODE_MODULES` to the directory containing `@oai/artifact-tool`. The runner resolves modules locally and does not install/download dependencies or upload portfolio content during a run. Before FT deployment, approve/provision this runtime or replace the presentation adapter with an approved XLSX writer. `run_model.ps1` is an optional Windows launcher; the Python commands above are the portable documented entry point.

Run tests with `python -m unittest discover -s tests -v`. [The validation report](docs/validation_report.md) records actual release evidence and limitations; test counts are not proof of agency calibration. Complete native Excel acceptance in the intended FT environment. Preserve the fictional baseline and keep real tapes, JSON results and reference outputs local.
