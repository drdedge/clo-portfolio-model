# Cash-flow engine: implemented conventions and calibration boundary

This document describes `clo/cashflow.py` and the delivered configuration. It is an independent deterministic development engine. It reports scenario payments, shortfalls, accounting checks and **first-failure default grid brackets**. It does not compute an exact continuous BDR, reproduce S&P Cash Flow Evaluator, estimate a CDO Evaluator SDR or determine an AAA rating. The definition of an agency BDR and related criteria versions are explained in `methodology.md`.

## Base configuration and provenance

| Item | Delivered base | Basis |
|---|---|---|
| Portfolio/as-of | Supplied fictional portfolio / 1 January 2027 | Supplied fictional workbook |
| Currency/benchmark | USD / SOFR | Supplied fictional workbook; single-currency processing |
| Capital | 64% senior, 26% junior, 10% equity | User-confirmed capital proportions; par funded |
| Senior sensitivity | 60%, 61%, ..., 70% | User range; equity fixed; junior residual |
| Note dates and day count | Quarterly, ACT/365 | Fictional development convention |
| Asset coupon dates | Quarterly or semiannual, anchored to as-of | Frequency supplied; phase/anchor invented |
| Legal final | 1 January 2039 | Fictional |
| Senior/junior margin | 140 / 550 bps | Fictional; benchmark floors 0% |
| Senior/subordinated fees | 35 / 15 bps per year on opening performing par | Fictional; fixed quarterly fee zero |
| OC / IC threshold | 1.25x / 1.20x | Fictional senior-only tests |
| Recovery | Facility `recovery_aaa`, four-quarter lag | Recovery values supplied fictional; lag invented |
| Base defaults | 30% of original par; front-loaded pattern | Severity fictional; timing from public table 20 |
| Prepayment | 0% per year | Explicit fictional setting |
| Reinvestment | Disabled because end date equals as-of | Explicit fictional setting |
| Principal support | Senior fees and senior interest may use principal | Fictional waterfall choice |
| Final liquidation | Remaining performing par at 100% | Fictional assumption, not a valuation |
| Opening cash | Zero | Required by this par-funded scope |

The model never treats the supplied asset `price` as a funding discount, sale price or coverage haircut. It is descriptive only. Facility `recovery_aaa` does not establish that S&P approved the recovery; automatic recovery-rating/lien/country classification is absent.

## Calendar and collateral engine

For period `n`, period end is three calendar months times `n` after the as-of date, clipped to legal final. Month-end days are clipped to valid calendar dates. Year fraction is actual elapsed days divided by 365. The final period may be a stub. Asset accrual stops at an in-period bullet maturity, although the associated cash is collected at that period end. These are synthetic payment conventions because contractual next-payment dates are absent.

Each facility starts with its supplied par, maturity, rate type, rate terms, recovery and payment frequency. Reinvestment creates additional homogeneous floating-rate cohorts. There is no stochastic issuer default draw and no rating-dependent hazard in the cash-flow module. Ratings affect descriptive credit and supplemental calculations elsewhere; a chosen cash-flow default fraction is an exogenous stress.

The period order is:

1. **Open balances.** Bring forward performing facility balances, unpaid asset coupon accrual, separate interest/principal cash and liability/fee arrears.
2. **Defaults at period start.** Requested defaults equal original portfolio par times cumulative severity times that period's timing weight. Actual defaults are capped at current performing par and allocated proportionately across all current facilities/cohorts. Every facility loses the same fraction of its then-performing balance. This is fractional pro-rata stress allocation, not whole-obligor Monte Carlo default simulation or the supplemental selected-obligor event scenario.
3. **Forfeit unpaid interest on defaulted principal.** Existing asset coupon receivables are reduced by the same fraction. Defaulted principal earns no current-period interest.
4. **Accrue surviving asset interest.** Floating coupon is `max(index, floor) + spread`, floored in total at zero; fixed coupon uses the supplied fixed rate, also floored at zero. Apply the surviving balance and actual accrual days/365.
5. **Maturity or prepayment.** An asset maturing by period end pays all surviving principal and coupon accrual. Otherwise apply `1 - (1 - annual_prepayment_rate)^year_fraction` to the surviving balance and collect that fraction of unpaid coupon accrual. A maturing asset does not also prepay.
6. **Coupon collection.** Quarterly assets pay every period. Semiannual assets pay every second quarter measured from as-of. The final period collects residual coupon accrual. Asset accrual is retained between scheduled dates and therefore is not immediately cash available to the waterfall.
7. **Recovery cash.** Each default creates a receivable equal to defaulted facility par times `min(1, recovery_aaa * recovery_multiplier)`. It pays at period `default_period + recovery_lag_quarters`; a zero lag means the end of the default period. Recovery is principal cash, recognized once. Receivables falling after legal final remain disclosed and are not available for final debt payment.
8. **Final liquidation.** At legal final, remaining performing par is removed and cash equal to par times `final_liquidation_price` enters principal proceeds. No recovery receivable is accelerated merely because legal final has arrived.

Requested defaults that cannot be placed are not silently moved to another period. The engine reports target default rate, realized default rate and unallocated default amount. A material unallocated amount makes the target unattained and blocks an exploratory pass, even if the lower realized defaults allow full payments. Defaults scheduled after legal final are likewise reflected in the final unmet target.

## Exact implemented waterfall

There are separate interest and principal cash accounts. No return is earned on idle cash or recovery receivables. The waterfall runs after current-period collateral collections.

1. **Senior fees.** Due amount equals prior unpaid senior fees, opening performing par times annual senior fee rate times period year fraction, plus fixed period fee. Pay from interest; if `principal_support_interest` is true, use principal for the remainder. Unpaid fees carry without compounding.
2. **Senior interest.** Accrue on opening senior note principal using `max(0, max(index, senior_floor_pct) + senior_coupon_bps/10000)`. Add prior unpaid senior interest. Pay only if senior fee arrears are within tolerance, first from interest and then optionally from principal. Prior arrears are paid before current coupon when measuring current timeliness. Arrears do not earn interest and do not capitalize into note principal.
3. **Coverage measurement.** IC numerator is remaining interest after senior fees and **before** senior interest. IC denominator is total senior interest due including prior arrears. OC numerator is post-default/post-maturity/post-prepayment performing par plus principal cash remaining after senior fees/interest plus `oc_recovery_credit` times outstanding recovery receivables. OC denominator is senior principal before any current diversion. A negligible/zero denominator gives an unavailable ratio. Failure means ratio strictly below threshold; equality passes.
4. **Interest diversion.** If either senior OC or IC fails, divert all remaining interest up to senior principal to repay senior principal. The failed test remains a distribution lock for the whole period. Tests are not iteratively recalculated to release a partial cure or resume junior interest in that period.
5. **Junior interest.** Accrue on opening junior principal with its benchmark floor and spread. Add unpaid junior interest without compounding or capitalization. Pay from remaining interest only when senior fees and senior interest are clear and no coverage test failed.
6. **Subordinated fees.** Due equals carried unpaid fees plus opening performing par times the subordinated annual fee and year fraction. Pay from interest only after senior obligations and junior interest are clear, and only when no test failed.
7. **Interest residual to equity.** Pay remaining interest to equity only after those obligations are clear and no test failed. Otherwise retain the interest account balance.
8. **Reinvestment.** Subject to the rules below, use remaining principal cash for collateral purchases.
9. **Principal sequence.** Remaining principal pays senior principal, then junior principal after senior principal is retired and senior fees/interest are clear. It then pays unpaid junior interest, and then subordinated fees after junior principal and interest are clear. Residual principal goes to equity only when senior/junior principal, senior fees/interest, junior interest and subordinated fees are clear. Retain any unused principal separately from interest.

Senior principal paid in the reported row includes the interest-diversion repayment plus repayment from principal cash. It must not be counted a second time as a separate cash use. With principal support disabled, the implemented principal sequence can retire senior principal while senior coupon arrears remain; it does not permit junior principal or equity principal in that situation. This is a development waterfall choice requiring indenture review, not an asserted S&P rule.

There is one senior OC/IC pair, not tranche-by-tranche coverage tests. Performing assets are carried at par. There are no CCC excess, purchase-price, discount-obligation, long-dated, workout-asset or special current-pay adjustments, and no junior test numerator/denominator. `oc_recovery_credit` is a generic fraction of modeled recovery receivables, not an implementation of every S&P/indenture defaulted-asset valuation rule.

## Reinvestment rule

Reinvestment occurs only when the period end is **strictly before** both `reinvestment_end_date` and legal final, with senior fee and interest arrears clear. When `reinvestment_stop_on_trigger` is true, a failed OC or IC blocks reinvestment. Otherwise the prototype can reinvest despite a failed test. All eligible remaining principal is used; there is no target-par cap, credit-quality test or portfolio reinvestment covenant.

Purchased par is principal cash divided by decimal `reinvestment_price`. A new floating cohort uses the configured spread, benchmark floor, recovery and maturity measured in rounded calendar months from purchase. It pays quarterly and starts earning in the following period. Reinvestment assets share subsequent fractional defaults. The rules and asset assumptions are identical across senior sizes; trigger-driven differences in reinvestment are endogenous effects of resizing.

The delivered base disables reinvestment by setting its end date to the as-of date. Reinvestment settings remain editable for exploration but do not establish the criteria's stable-quality/CDO Monitor treatment.

## Scenario matrix and reported default-capacity bounds

The twelve delivered scenarios combine four table 20 annual timing patterns with constant index rates of 0.5%, 3% and 6%. Each annual default share is split equally over four quarters. These fictional rate paths are not S&P's rising, falling, rising/falling, falling/rising and forward stress set. They do not include benchmark basis risk, curve calibration, rate reset conventions or hedge cash flows.

Each senior size is tested at configured severities, initially 0%, 5%, ..., 100%. The base severity is also run even if it is not a grid point. Base details are retained for the chosen base size/scenario; all grid summaries and scenario boundaries are retained in results JSON.

`boundary_from_grid` identifies the first attained target with a senior failure and the last preceding attained passing grid point. It returns the **tested interval**, not an interpolated default capacity. A pass after a failure makes the grid non-monotonic and suppresses a scalar bracket. Unattainable targets can also make a boundary unavailable. A scenario passing every feasible grid point is not automatically assigned 100% capacity. No bisection search or globally valid BDR estimate is performed.

The binding base scenario prioritizes invalid/unattained cases and shortfalls. If all base-severity scenarios pass, the engine reports a scenario with an unresolved boundary or the lowest first-failure bracket, with deterministic ties. The binding basis is retained in the result packet and should be read alongside the scenario name. A base shortfall and the limiting grid bracket answer different questions.

## Controllable inputs and precedence

| Control group | Configuration / workbook fields | Important rule |
|---|---|---|
| Dates and sizing | `as_of_date`, `legal_final_date`, `base_senior_pct`, `equity_pct`; `senior_sizes` in JSON | Senior must stay within 60%-70%; junior is residual; opening cash remains zero |
| Coupons and fees | Senior/junior coupon bps and floors; senior/subordinated fee bps; fixed fee per period | Annual fractions internally; fees use opening performing par; no arrears compounding |
| Coverage | `oc_trigger`, `ic_trigger`, `oc_recovery_credit`, `principal_support_interest` | Senior-only simplified tests and disclosed waterfall |
| Recoveries | Facility `recovery_aaa`; `recovery_lag_quarters`; scenario `recovery_multiplier` | Scenario multiplier affects original and purchased assets, capped at 100% |
| Rates | Scenario `index_rate_path` in Stress Inputs; global fallback in JSON | Scenario path overrides global; after path end, its last rate repeats |
| Defaults | Scenario `default_weights`; `base_default_rate`; `stress_default_rates` in JSON | Weights are fractions of cumulative defaults, not conditional default hazards |
| Prepayment | Scenario `annual_prepayment_rate`, then global fallback | Every delivered scenario sets its own value, so changing only the global value does not alter those scenarios |
| Reinvestment | End date, price, spread, recovery, maturity, floor and stop-on-trigger flag | Synthetic homogeneous cohorts; no CDO Monitor or credit-quality maintenance |
| Final assets | `final_liquidation_price` | Applies only to surviving performing par at legal final |

The scalar workbook assumption table and scenario overrides identify editable values. Structural arrays such as senior sizes, grid severities, vocabulary lists and column mappings are JSON-controlled. Portfolio edits must be made in CSV and regenerated. Existing workbook assumptions can be imported using the documented `--assumptions-from` option; all dependent Python results require a rerun.

## Validation and interpretation

The cash-flow engine reconciles period cash sources/uses, performing par, recovery receivables, unpaid asset interest, nonnegative balances and capital proportions. It checks the implemented junior/equity priority restrictions. Tolerance is the greater of 0.01 currency unit and original par times `1e-10`. The senior scenario passes only if accounting checks pass, the default target is attained, no current senior coupon was missed and all senior principal/interest is paid by legal final. A later cure does not erase a previous timeliness failure.

The distinction between accounting validity and economic sufficiency is deliberate: a severe stress can conserve every unit of cash while still causing note shortfalls. Likewise, an unattainable default target is not a valid stress pass. Excel provides independent equations for the detailed base run; Python checks cover the grid. Formula refresh flags identify changes relative to stored run inputs but are not independent validation of the underlying finance model.

## FT calibration and remaining agency features

Before relying on real-data calibration, reconcile the source/version register, issuer rating hierarchy and mapping, official industry codes, recovery-rating/point-estimate hierarchy, covenant-lite/lien status and recovery country groups. Then validate actual payment dates, day counts, amortization, call/extension treatment, reinvestment conditions, fee priorities and coverage mechanics against the deal.

Obtain approved rate stresses and evaluator outputs. The optional AAA SDR already requires source and evaluator/model-version provenance, an as-of date matching the run, the pinned criteria revision, and matching raw CSV and normalized credit-input SHA-256 hashes. The normalized hash includes facilities, as-of date and criteria revision. The runner rejects missing or mismatched bindings, including changes that leave the CSV unchanged but alter normalized inputs or valuation date. FT review must still authenticate the external evidence and validate calibration. The external value remains a supplied input; accepting it produces no exact BDR comparison or AAA conclusion.

Further work includes appropriate reinvestment-period amortization curves, eligible-investment earnings, full payment-frequency mismatches, default bias, funded/unfunded commitments, PIK/defaulted/current-pay/workout assets, discount/CCC/long-dated coverage adjustments, multiple tranches, hedges and FX. Supplemental selected-obligor/industry default events need approved waterfall runs before assessing sufficiency. Related counterparty, sovereign, legal and manager/operational reviews are separate dependencies.

Calibration should compare period cash ledgers before aggregate results, preserve discrepancy explanations, and extend tests whenever scope changes. This build provides transparent mechanics and a reproducible fictional baseline for that work; it does not certify agency equivalence.
