# Executed validation report

Executed locally on 21 September 2026 with fictional data only. No attachment was uploaded or changed. This establishes tested implementation behavior, not credit-model calibration or agency validation.

## Workflow demonstration

The documented Python command generated `examples/Example_CLO.xlsx` from `examples/example.csv`. Replacing the CSV argument with `examples/replacement.csv` successfully generated `examples/Replacement_CLO.xlsx`, including resized input tables, formula ranges, obligor aggregation, all senior sensitivities and base cash flows. The blank reusable workbook was generated with `--template`.

| Portfolio CSV | Facilities | Obligors | USD par | Stress runs | Accounting failures | Unattained severity targets |
|---|---:|---:|---:|---:|---:|---:|
| example.csv | 282 | 270 | 300,000,000 | 2,772 | 0 | 297 |
| replacement.csv | 52 | 50 | 55,744,000 | 2,772 | 0 | 330 |

Unattained targets are disclosed outcomes, not accepted passes. For example, scheduled defaults at very high severities can exceed surviving collateral after maturities. They are excluded from valid cash-flow passes and qualify the grid boundary where relevant.

The larger replacement fixture (564 facilities, 540 obligors, USD 600 million par) also passed the actual command-line validation path. A separate 601-row input test verifies there is no fixed original-row limit. The larger fixture was validated, not presented as a completed cash-flow workbook.

The deliberate-error CSV produced **5 specific row/field errors**. No invalid workbook was published. Tests also verify that existing completed workbooks/results survive input, renderer and publication failures, including rollback after a partially attempted publication.

## Automated tests

**117 tests passed** using `python -m unittest discover -s tests -q`.

Coverage includes required/conditional fields, units, leading-zero IDs, aliases and column mappings, duplicate facilities, common-obligor grouping, unsupported categories, invalid dates/configuration types, missing deal assumptions, nonfinite values, external SDR provenance and input binding, input/output path collisions, literal Excel import, transaction rollback, public supplemental stress counts and recoveries, default timing, recovery receivables, coupons, waterfall priority, OC/IC diversion, prepayments, reinvestment, timely interest, nonmonotonic grids and unattainable default targets.

## Excel verification

All three final workbooks contain **21 sheets and 67 named ranges**. The example contains 8,560 formulas, the replacement 3,076 and the blank template 847. Formula/error scans found no Excel error cells. The completed example and replacement have no unexpected failed reconciliation checks. Cash-flow formula checks independently reconcile cash, collateral, senior/junior principal, recovery receivables, asset coupon receivables, coverage triggers and waterfall priority. The empty template displays NOT RUN and requires a refresh.

All 21 sheets were rendered and visually reviewed. Each workbook has 37 rendered views covering sheet layouts plus source/formula columns, all assumption rows, cash-flow sections, concentration chart, default boundaries, methodology/gap sources and the opening guide. Source-note clipping and date presentation found in review were corrected and rendered again. Repeating data-table rows were checked programmatically throughout, with representative rows reviewed visually. Frozen panes, numeric/date formats, distinct agency tab colours and saved automatic recalculation flags were inspected. Verification used the local spreadsheet calculation/rendering library and saved XLSX inspection; this was **not** a native Microsoft Excel application recalculation session.

Editing a senior-sizing assumption, a rate-path input or a portfolio par value triggered REFRESH REQUIRED. The portfolio total recalculated from the edited balance. Inputs were restored before final export. The saved workbook's assumption-import round trip preserved the original configuration hash exactly.

The release also verifies that Fitch input and agency factor-table edits trigger refresh, missing scalar/scenario assumption rows fail import, and an imported S&P SDR is suppressed when its portfolio is stale. Excel SPWARF, S&P dispersion and Fitch WARF reconcile independently to Python. Incomplete Fitch recovery coverage suppresses whole-portfolio WARR. Complete saved-example and replacement assumption imports preserved their configuration hashes.

## Separate agency inputs and calculations

Example SPWARF is **2,379.38** and S&P default-rate dispersion is **827.21** on the published performing-factor basis. Fitch WARF is **21.428949**, explicitly based on development rating proxies. The two WARFs have different scales.

Fitch recovery coverage is **98.5447% of par**; seven facilities need recovery classification, so WARR remains unavailable. Fitch industry inputs are absent. Replacement Fitch WARF is **20.401937** and recovery coverage **96.6884%**, with WARR also unavailable. Neither example contains S&P SDR or Fitch PCM RDR/RLR, and neither produces an agency BDR or AAA conclusion.

CLI tests execute missing and supplied Fitch overlays, invalid fields and duplicate IDs, and input/output collisions. They verify source hash/path retention, preservation of completed artifacts after errors, no automatic S&P substitution, unchanged S&P metrics/cash flows when the Fitch overlay changes, and a distinct run identity for a different overlay.

A separate saved-workbook test changed the senior margin from 140 to 200 bps. The imported assumption reached the Python waterfall, changed equity distributions from USD 110,023.63 to USD 0.00, and preserved accounting reconciliation. This is an implementation check, not an economic forecast.

## Fictional example interpretation

At 64% senior sizing and the configured 30% cumulative-default base case, senior timely-interest and ultimate-principal shortfalls are zero. Across the configured profiles, the lowest first-failure grid interval is 60%–65% defaults. These are **exploratory tested-grid results**, not S&P BDRs, SDR comparisons, ratings or evidence of AAA sufficiency. The input recovery values, rate paths and deal terms require approved calibration before real-data use.

Main run ID: `c31d923d2a5ee803`. Replacement run ID: `fb584e4d70c74a8b`. CSV/config hashes and full machine-readable results accompany each workbook. The renderer runtime must be separately approved and provisioned for FT deployment, as described in the operating instructions.
