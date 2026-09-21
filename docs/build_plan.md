# Methodology-first build plan and delivered architecture — release 0.2.0

This plan records the fictional local model and distinguishes it from pending FT calibration. Release 0.2.0 adds verified S&P credit metrics and a separate Fitch public-metric module to the shared portfolio processor, formula-driven Excel review model, S&P concentration calculator and independent cash-flow engine. One workbook provides both agency views and combined outputs. It is not an agency model or rating tool.

## 1. Establish the specification and methodology boundary

**Delivered.** Read the requested S&P criteria first and matched the supplied 66-page PDF. The pinned source is the 21 June 2019 criteria, republished **10 April 2026**, article 3547721. The source register and expanded requirement mapping are in `methodology.md` and `methodology_map.csv`. The supplied **English Fitch criteria dated 1 June 2026** provide separate Appendix 6 public factors and related references. Fitch does not supply S&P parameters. S&P rating factors are verified against a primary issuer filing with agency definitions documented separately.

The user clarified that no separate build brief, model configuration or internal-calibration findings existed. The request and S&P source therefore establish the build specification. The supplied example is fictional and remains unvalidated as a tail-risk calibration. No real portfolio was required for development.

The design explicitly separates:

| Layer | Delivered result | Meaning |
|---|---|---|
| Shared portfolio analysis | Formula-based composition, grouped exposure, spread, remaining term, recovery and concentration summaries | Descriptive characteristics of the supplied tape |
| S&P credit metrics | SPWARF and default-rate dispersion from a verified public factor scale | Performing benchmark scope; not an SDR |
| Fitch credit metrics | WARF/WARR formulas from separate Fitch inputs and public factors; coverage/provenance exposed | Whole-portfolio metric requires complete relevant input coverage; proxy examples remain development assumptions |
| S&P SDR | Unavailable by default; optional externally supplied value with enforced provenance/input binding | No CDO Evaluator simulation or calibrated agency SDR is generated |
| Fitch PCM thresholds | RDR/RRR/RLR unavailable | No PCM tail distribution or full Fitch analysis is generated |
| Cash-flow default capacity | Scenario shortfalls and exploratory first-failure grid brackets | Conditional result from this independent waterfall and the tested grid; no exact maximum BDR is claimed |
| Supplemental tests | Public rating-band obligor and industry loss arithmetic | Event stresses, with no tranche cash-flow sufficiency conclusion |
| Rating outcomes | S&P and Fitch AAA not determined | Targets, not assigned ratings |

**FT refinement.** Approve the target transaction scope, licensed/authorized agency inputs, current source versions and model acceptance criteria before calibration. Related legal, operational, counterparty and sovereign analyses remain outside the numerical prototype; the related criteria register identifies these dependencies.

## 2. Define the input and configuration contracts

**Delivered.** Retain the supplied portfolio's eighteen raw fields in a canonical UTF-8 CSV. One row is one facility; a common obligor ID groups facilities. Preserve text IDs, including leading zeroes. Use currency units for par, basis points for spreads/floors, decimal fractions for fixed coupons/recoveries, price per 100 for descriptive price and ISO dates. All headers are required; fixed/floating fields can be blank only when inapplicable.

`clo/inputs.py` validates required fields, finite values, ranges, rating symbols, country/industry/seniority vocabularies, supported currency/benchmark, date order, coupon frequency, facility uniqueness and obligor consistency. Case/whitespace normalization and configured aliases are logged. Column mapping and unit multipliers are configuration data; replacement CSVs do not require code changes. Unknown categories and missing economics block the run.

The code preserves separate facility maturities, coupons and recoveries. Obligor-level issuer rating, industry, country and name must agree within a group. It does not average inconsistent issuer ratings or use facility identity as the common-default grouping key. Ratings below CCC-, defaulted/unrated exposure and unsupported currencies are rejected.

Fitch information uses an explicitly selected optional `--fitch-inputs` sidecar keyed to `instrument_id`. Its seven fields are documented in `templates/fitch_inputs_dictionary.csv`. `clo/fitch.py` rejects duplicate/unmatched IDs, malformed supplied values and conflicting obligor-level inputs. Missing Fitch fields create metric-specific coverage gaps rather than silent substitutions or a fabricated whole-portfolio average. No sidecar filename is inferred. The shared CSV remains compatible and authoritative for collateral economics.

The example sidecar contains explicit development rating proxies, 98.5447% recovery-par coverage and no industry mapping. Its numeric WARF is therefore a development calculation; WARR is unavailable. Seven ambiguously classified assets have no recovery assumption. Missing Fitch input is not a Fitch pass or failure. Source references label assumptions but are not independently authenticated by the parser.

Configuration in `config/model.json` supplies explicit development deal terms, scenario arrays, mappings, permitted vocabularies and provenance. The base structure is the user-confirmed **64% senior / 26% junior / 10% equity**. Senior varies from **60% to 70%**, equity remains 10%, and junior is the residual. All sizes fund the same original collateral par.

An external AAA SDR is accepted only with source and evaluator/model-version provenance, a matching as-of date and pinned criteria revision, and matching SHA-256 hashes of both the raw CSV and normalized facility/date/revision snapshot. The runner enforces these bindings. They detect mismatched inputs; they do not authenticate the external source or validate its calibration.

**FT refinement.** Replace example vocabulary lists with reviewed official S&P industry codes, country groups and reliable source mappings. The current list admits the fictional source labels and does not prove their S&P classification. Add contractual payment dates, day count, amortization, rating sources/watch, recovery indicators/point estimates, covenant-lite status, asset eligibility and deal-specific fields through a versioned schema extension rather than hidden defaults.

## 3. Keep processing and model calculations local

**Delivered architecture.**

| Component | Responsibility | Inputs and outputs |
|---|---|---|
| `clo/__main__.py` | One-command orchestration, optional Excel assumption import, validation report, run identity and atomic workbook replacement | Shared CSV + optional Fitch CSV + JSON (+ designated saved Excel inputs) to results JSON, validation JSON and workbook |
| `clo/inputs.py` | Strict ingestion, normalization, configuration checks and descriptive aggregation | Raw rows to normalized facilities, obligors, summaries and normalization log |
| `clo/methodology.py` | Versioned S&P SPWARF/dispersion, public concentration arithmetic and reference helpers | Normalized corporate exposures to public credit metrics and event-scenario audit |
| `clo/fitch.py` | Separate Fitch input validation and public WARF/WARR calculation | Shared facility identity/par + explicit Fitch sidecar to metrics, coverage, provenance and missing-input register |
| `clo/cashflow.py` | Deterministic period simulation, stress matrix and first-failure bracket analysis | Facilities + deal assumptions + scenario + senior size to periodic flows and checks |
| `build_workbook.mjs` | Excel formulas, formatting, tables, charts, refresh flags and local render/export | Auditable result packet to review workbook |
| `tests/` | Input, configuration, CLI, accounting, stress-boundary and methodology regression tests | Fictional controlled fixtures; no private calibration data |

The Python engine uses the standard library for ingestion and simulation. Reading a saved workbook's literal assumption cells requires `openpyxl`. Excel generation uses a local Node runtime and `@oai/artifact-tool`; these dependencies must be available in the destination environment. The process does not download dependencies or upload portfolio content during a model run. `--engine-only` can generate auditable JSON without the Excel renderer; it does not satisfy the full Excel deliverable on its own.

**FT refinement.** Provision and approve both Python and the local workbook renderer before transfer, or replace only the presentation adapter with an approved Excel writer while preserving the Python/result contract and formula tests. Confirm package/license availability and offline reproducibility within FT. A workbook that relies on a Codex runtime path is not automatically portable to a clean machine.

## 4. Implement and expose the cash-flow contract

**Delivered.** Quarterly note dates use a calendar-month schedule from the as-of date, with ACT/365 accrual. Assets support quarterly and semiannual payment frequency, anchored synthetically to that date. Facility bullet maturities, interest accrual, fractional period-start defaults, recovery receivables, annual-to-period prepayment conversion and optional reinvestment are explicit. The configured base has no reinvestment and no prepayment; those are labelled development settings, not inferred absences.

The two debt tranches have editable coupons, fees, recovery lag, interest paths, coverage triggers, principal support and reinvestment rules. Senior interest timeliness and ultimate principal are tested separately. Junior arrears and principal shortfalls are reported, with no junior rating conclusion. All formulae, timing choices and the exact waterfall order are documented in `cashflow_design.md`.

The standard matrix crosses four published S&P table 20 timing patterns with three fictional constant index paths, then evaluates senior sizes and a fixed default-severity grid. The same source facilities and stress/deal assumptions apply to each size. A signature excludes the size controls to make that consistency auditable. If coverage triggers alter reinvestment, resulting collateral differences are consequences of the same rules, not manually changed input stress.

The Fitch overlay does not create a second cash-flow model or establish Fitch stress compliance. Its metrics remain separate from the orange development cash-flow sheets. A future Fitch module must implement its own applicable scenarios and compare like-for-like portfolio hurdles and tranche capacities; it must not rename these existing exploratory results.

**FT refinement.** Reconcile actual indenture priorities and payment promises, calibrated rate paths, recovery hierarchy/timing, reinvestment constraints, amortization and coverage numerator/denominator definitions. Evaluate default bias toward high-spread, low-recovery, fixed-rate or concentrated subsets as applicable. These extensions need new assertions and regression fixtures, not a change of label from exploratory to agency-aligned.

## 5. Build the formula-driven Excel review model

**Delivered.** The workbook contains 21 sheets, retaining all fifteen legacy names and adding `Agency Comparison`, `SP Credit Parameters`, `Fitch Inputs`, `Fitch Parameters`, `Fitch Calc` and `Gaps and Sources`. Start with Read Me and Agency Comparison. The complete role/colour map is in [README](../README.md) and the workbook's Read Me. Shared inputs, agency calculations and development cash-flow outputs are clearly distinguished.

Excel formulas calculate weights, remaining terms, weighted spread/recovery, composition, obligor sums, HHI/effective obligors, capital balances, SPWARF/dispersion, Fitch WARF/WARR/coverage and reconciliation equations. Parameter tables expose the source factors. Python independently supplies public metrics plus simulations, selected supplemental exposures and stress-grid results. A rebuild constructs tables/formula bounds from the current row count; manual row insertion is not the refresh workflow.

Blue/amber cells identify editable assumptions. Imported and Python values use a distinct fill. Baseline run values and the imported portfolio snapshot support change detection. Output sheets show refresh warnings and headline results are gated where applicable. Formula-based flags require Excel automatic recalculation. Changing an editable value does not run Python inside Excel.

The supported round-trip reads literal values from designated `Assumptions` and `Stress Inputs` cells with `--assumptions-from`. Shared and Fitch CSVs remain their respective input authorities. Editing Fitch Inputs in Excel does not persist to the next run: edit the sidecar to retain changes. Parameter tables are sourced constants, not an override interface; reconciliation detects modifications. Formulas in editable imported assumption cells are rejected. Scenario identity/period changes require the configuration workflow.

**FT refinement.** Validate refresh warnings and formula behavior with the approved Excel version, including saved-workbook changes, new CSV row counts and altered date/rate inputs. Treat snapshot sheets as an audit aid, not tamper-proof evidence; keep immutable source and run files under local governance.

## 6. Validate in distinct layers

**Tests and fixtures.** The suite covers invalid input/configuration, duplicate facilities versus repeated obligors, unsupported ratings/frequencies, zero/default extreme cases, recovery timing, coupon accrual, timely interest, fees/priority, coverage diversion, reinvestment, conservation and non-monotonic/unattainable grids. Public methodology cases check concentration mechanics, verified SPWARF factors and dispersion. Fitch cases cover factor scale, complete versus missing metrics, provenance basis, duplicate/unmatched IDs and obligor consistency. These cases are implementation tests; actual executed release evidence belongs in `validation_report.md`.

Fictional workflow fixtures include:

| Fixture | Facilities | Obligors | Purpose |
|---|---:|---:|---|
| Supplied example conversion | 282 | 270 | Preserve raw inputs from the user's fictional workbook |
| Smaller replacement | 52 | 50 | Rebuild with fewer rows while retaining common-obligor facilities |
| Larger replacement | 564 | 540 | Rebuild with more rows using separately identified copies |
| Deliberate-error CSV | 6 | Not valid | Reject duplicate ID, missing recovery, invalid rating/date and negative par |

No test fixture establishes statistical or cash-flow equivalence to a real portfolio. Final workbook generation, formula inspection, visual QA and replacement-run evidence belong in the delivery validation record; the presence of a test file alone is not evidence that all checks passed.

**Acceptance sequence.** Validate inputs; reconcile raw and normalized totals; reconcile obligors; inspect assumptions/provenance; run module tests; generate example; replace CSV and regenerate; inspect changes in table/range bounds; exercise invalid input and confirm the prior workbook remains intact; change a designated Excel assumption and verify refresh/re-run behavior; review formula errors and sample rendered sheets. Record commands, run hashes and outcomes in the local delivery evidence.

## 7. Handoff to FT calibration

The following is controlled refinement work, not a statement that the fictional model meets either agency's complete criteria:

1. Freeze the approved model version, source register, schema, dependencies and benchmark dataset. Keep all real tapes and calibration material inside the approved environment.
2. Reconcile issuer keys, agency-specific rating provenance/classifications, currencies and maturity/recovery inputs against approved sources. Repeated facilities must share the intended common-default obligor. Complete Fitch recovery/industry coverage and replace development rating proxies; retain separate agency bases.
3. Obtain authorized CDO Evaluator outputs and relevant public/proprietary parameters. Supply the provenance and matching bindings already required by the runner: source, evaluator/version, criteria revision, as-of date, **normalized credit-input snapshot** and original CSV hash. Verify the external evidence and calibration independently. Changing a mapping or as-of date can change credit analysis even when CSV bytes do not change.
4. Compare public supplemental stress selections and loss amounts independently before integrating event scenarios into the approved waterfall. Verify both industry routes and all rating bands.
5. Reconcile cash-flow periods to contractual schedules and the indenture. Compare cash sources/uses and trigger outcomes by period before comparing any aggregate default-capacity measure.
6. Expand to all applicable calibrated scenarios, including current benchmark stress paths and approved recoveries; assess timing, prepayment, reinvestment and default-bias effects. Handle infeasible/default-allocation paths explicitly.
7. Establish a justified default-capacity search/resolution and comparison convention. The current coarse grid is evidence about tested points, not proof of an exact continuous BDR.
8. Add authorized Fitch PCM outputs or a benchmarked independent implementation, plus applicable Fitch stress/waterfall analysis, before making Fitch sufficiency comparisons. Current public factors alone do not supply this analysis.
9. Obtain model-risk review and complete relevant legal, manager/operational, counterparty and sovereign work. Only the appropriate agency process can assign an agency rating.

The immediate reusable workflow is complete when a validated replacement CSV produces a fresh checked workbook with a new run identity. Promotion from development analysis to approved real-data calibration is a separate, documented decision with the gaps above resolved.
