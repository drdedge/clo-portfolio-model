# Outstanding work and next steps — release 0.2.0

The model uses one workbook for shared portfolio/deal inputs, distinct S&P and Fitch calculation areas, and combined results. It does not reproduce either agency's complete rating process. S&P's core source is the criteria originally published 21 June 2019, republished 10 April 2026. The controlling Fitch source is the supplied English CLO criteria PDF dated 1 June 2026.

## What the results mean

**Credit-quality measures:** SPWARF and Fitch WARF summarize ratings on different factor scales. They are not directly interchangeable. S&P's public factors are implemented. Fitch WARF and WARR require complete applicable inputs, with provenance; otherwise the relevant whole-portfolio metric is not assessed. WARR aggregates recovery assumptions, not tail losses. An explicitly fictional Fitch sidecar can demonstrate arithmetic without becoming a verified credit assessment.

**Portfolio hurdle:** S&P SDR is a cumulative gross default hurdle for the rating stress. It depends on the collateral, not the chosen senior debt size. Fitch PCM's rating default rate (RDR) and rating loss rate (RLR) are separate quantities. RLR is recovery-adjusted and cannot be compared directly with gross default capacity.

**Cash-flow capacity:** BDR asks how much default the tranche can withstand while meeting its payment promises under specified scenarios. The engine reports exploratory tested default-capacity intervals, not a formal S&P or Fitch BDR. Its 30% base default severity is illustrative, not an SDR/RDR.

S&P SDR is not generated internally. Fitch PCM RDR/RLR and formal agency BDRs are unsupported. Neither agency's AAA outcome is determined. Non-model CDO Monitor research remains separate; it is not a delivered replacement for initial rating analysis.

## What can be finished, and what must be supplied

| Work | Source / owner | Next action |
|---|---|---|
| Complete Fitch coverage | FT credit master, Fitch rating/recovery sources and classification mapping | Populate the separate facility overlay. Resolve gaps explicitly. Do not silently copy S&P ratings, recoveries or industries. |
| Recovery hierarchy | Published rules plus recovery opinions, lien priority, covenant-lite status and jurisdiction | Verify applicable selection rules. “Senior” alone cannot determine recovery. Keep development overrides identified. |
| Contractual asset cash flows | Asset system/credit agreements | Add payment/reset dates, day-count, amortisation and accrued interest. The eighteen-field tape omits these contractual details. |
| Debt/waterfall/coverage | Term sheet/indenture and trustee definitions | Replace fictional terms; implement actual numerator adjustments, cure priority and tranche promises. |
| Managed-portfolio treatment | Reinvestment covenants and applicable agency methodology | Choose static run-off, maintained-quality or stressed-covenant analysis. Today's tape does not establish future collateral quality. |
| Full agency scenario sets | Criteria, dated market curves and trusted reference runs | Establish each agency's rate/default/recovery timing, prepayment and bias stresses. Keep existing exploratory scenarios distinct. |
| Capacity and event cash flows | Model development using agreed deal/scenario rules | Refine the search and pass selected-obligor/industry events through the waterfall. Loss arithmetic alone is not payment sufficiency. |
| Portfolio tail thresholds | Authorized agency tools/outputs or independently benchmarked implementation | Source matching S&P SDR and Fitch PCM RDR/RLR. Public methodology components can be coded; exact equivalence requires evidence. |
| Portable workbook and Excel acceptance | FT runtime policy and Excel version | Provision/replace the Node renderer; verify formulas, refresh flags and imports in target Excel. |

Public calculations and engineering can proceed with fictional data. Deal facts must come from source records. Additional currencies, defaulted assets and extra liability classes are needed only when included in the agreed scope.

## Current fictional baseline

The user confirmed 64% senior / 26% junior / 10% equity; senior varies 60%–70%, equity stays fixed and junior is residual. The example supplies USD/SOFR and 1 January 2027 as-of.

Other base terms are fictional: 1 January 2039 legal final; senior/junior margins 140/550bp; senior/subordinated fees 35/15bp; senior OC/IC 1.25x/1.20x; quarterly ACT/365 notes; four-quarter recovery delay; no prepayment or reinvestment; 30% defaults; index paths of 0.5%, 3% and 6%; and final liquidation of surviving assets at par. They are editable development choices, not agency-approved assumptions.

The example Fitch rating proxy is explicitly a development mapping from the fictional S&P ratings. Recovery assumptions cover 275 facilities and 98.5447% of par; seven unresolved facilities keep whole-portfolio WARR unavailable. Industry coverage is 0%. The S&P AAA recovery field must not become Fitch's recovery input by default.

## Minimal information to assemble locally at FT

1. Target portfolio/deal scope and unsupported features that are actually required.
2. Debt, fee, waterfall, coverage and reinvestment term sheet/indenture provisions.
3. Agency rating/recovery/classification data and contractual payment schedules.
4. Any authorized reference run, including matching portfolio, settings and model version.
5. Approved Python, workbook renderer and Excel environment.

Keep real data and reference results inside FT. Reconcile inputs first, period ledgers second, and headline thresholds last. Tests establish coded behavior, not agency-model equivalence. See [the operating guide](../QUICK_START.md) and [LLM handover](LLM_HANDOVER.md).
