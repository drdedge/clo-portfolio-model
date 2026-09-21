# User guide — release 0.2.0

## 1. Open and orient

Open `examples/Example_CLO.xlsx`. Start with **Read Me**, then **Agency Comparison**, then **Portfolio Inputs**, **Fitch Inputs** and **Assumptions**. **Outputs** contains portfolio/development results; it is not an agency rating page.

There is one shared portfolio and capital structure, separate S&P/Fitch metric areas and an independent development waterfall. The base is 64% senior / 26% junior / 10% equity. Senior varies 60%–70%, with equity fixed and junior residual. AAA is not determined for either agency.

## 2. Prepare your input files

Copy `templates/portfolio_template.csv` and follow [the shared data dictionary](docs/data_dictionary.md). Keep all eighteen headers, one unique facility ID per row and the same obligor ID for related facilities. Enter par in full currency units, spreads/floors in bps, recoveries in fractions and dates as `YYYY-MM-DD`. Missing economics must not be replaced by zero. Configure alternate headers/units in `config/model.json`.

For Fitch, copy `templates/fitch_inputs_template.csv` and use [its dictionary](templates/fitch_inputs_dictionary.csv). Match facility IDs to the shared CSV. Supply separate Fitch rating, rating basis, industry, recovery, recovery basis and source reference where available. Do not copy the S&P AAA recovery column. Missing Fitch information remains visible; duplicate/unmatched identifiers and malformed entries must be fixed.

The fictional Fitch example contains labelled rating/recovery proxies. Recovery coverage is 98.5447% with seven unresolved facilities, so whole-portfolio WARR is unavailable; industry coverage is 0%. It demonstrates public formulas from the supplied English Fitch criteria dated 1 June 2026, not verified Fitch credit opinions. Omitting the Fitch CSV still generates the workbook with missing Fitch analysis identified.

## 3. Run the process

From the package folder, validate your selected files first:

```powershell
python -m clo --portfolio examples/replacement.csv --fitch-inputs examples/fitch_replacement.csv --config config/model.json --output Updated_CLO.xlsx --validate-only
```

Then generate the workbook by removing `--validate-only`:

```powershell
python -m clo --portfolio examples/replacement.csv --fitch-inputs examples/fitch_replacement.csv --config config/model.json --output Updated_CLO.xlsx
```

Replace the paths with your new CSVs. Omit `--fitch-inputs` when no overlay is available; no matching filename is inferred. Row counts and formula ranges rebuild automatically. Successful output includes Excel, a results JSON and a validation JSON. Errors identify affected rows/fields; a failed run preserves an existing completed workbook.

## 4. Check before interpreting

Open **Checks** and **Gaps and Sources**. Resolve invalid inputs, reconciliation errors, unexpected parameter changes and **REFRESH REQUIRED**. A missing methodology component is a disclosed gap, not a numerical pass.

In **Agency Comparison**, inspect each metric's coverage, basis and status. Numeric SPWARF/Fitch WARF summarize ratings on different scales; WARR summarizes applicable recoveries. They are not SDR/RDR/RLR or agency ratings. Fitch WARR stays unavailable if relevant portfolio inputs are incomplete.

Use **Cash Flow Calc**, **Sensitivity** and **Stress Results** for development payments, shortfalls, binding scenarios and tested default-capacity intervals. The tests hold the same starting collateral/stress rules across senior sizes. A reconciled cash flow can still have a shortfall; an unattained default target is not a pass. The default grid is not an exact agency BDR.

## 5. Edit and rerun

Blue text/amber cells on **Assumptions** and **Stress Inputs** are supported editable controls. Save the workbook, then import those designated literal cells:

```powershell
python -m clo --portfolio examples/replacement.csv --fitch-inputs examples/fitch_replacement.csv --config config/model.json --assumptions-from Edited_CLO.xlsx --output Refreshed_CLO.xlsx
```

Live formulas recalculate in Excel; Python simulations require the rerun. Use automatic Excel calculation. Shared portfolio edits belong in the shared CSV. Fitch edits belong in the Fitch CSV: changes made directly to **Fitch Inputs** are not imported by `--assumptions-from` and will be replaced on regeneration. Parameter sheets are sourced references, not an assumption-editing interface. Structural scenario/mapping changes belong in JSON.

## Setup and handoff

Python runs the engine; saved-assumption import needs `openpyxl`. Excel generation also needs approved local Node plus `@oai/artifact-tool`, whose binaries are not in the ZIP. See [README](README.md) for runtime paths and engine-only use. No portfolio upload is required. Keep source files, workbook and JSON results together inside the approved environment.

Read [Outstanding work](docs/OUTSTANDING_AND_NEXT_STEPS.md) before replacing fictional terms with real deal data. Give [LLM_HANDOVER.md](docs/LLM_HANDOVER.md) and this package to the next developer/assistant. The test command is `python -m unittest discover -s tests -v`.
