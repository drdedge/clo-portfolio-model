"""Deterministic, exploratory CLO cash flows. This is not an agency model.

Defaults are fractional pro-rata amounts of original portfolio par, paid coupons
use ACT/365, and recoveries use facility-supplied ``recovery_aaa`` assumptions.
Senior interest is tested for timeliness; senior principal is tested at legal final.
All portfolio processing is local. The module uses only the Python standard library.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import math
from datetime import date
from typing import Any


def _date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _rate(path: list[float], index: int) -> float:
    return float(path[min(index, len(path) - 1)])


def _signature(facilities: list[dict], config: dict, scenario: dict, severity: float) -> str:
    # Deal sizing is excluded; starting collateral and all stress/deal assumptions
    # remain included. This proves identical inputs, not identical trigger outcomes.
    ignored = {"base_senior_pct", "senior_sizes", "senior_pct", "output_path"}
    body = {"facilities": facilities,
            "config": {k: v for k, v in config.items() if k not in ignored},
            "scenario": scenario, "default_rate": severity}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _validate(facilities: list[dict], config: dict, senior_pct: float,
              default_rate: float, scenario: dict) -> None:
    if not facilities or sum(float(f["par"]) for f in facilities) <= 0:
        raise ValueError("Cash flow requires positive portfolio par.")
    if int(config.get("periods_per_year", 4)) != 4:
        raise ValueError("The implemented engine uses quarterly payment periods only.")
    if not 0 <= default_rate <= 1:
        raise ValueError("default_rate must be a decimal fraction from 0 through 1.")
    equity = float(config["equity_pct"])
    if not (0 < senior_pct < 1 and 0 <= equity < 1 and senior_pct + equity <= 1):
        raise ValueError("Senior debt, residual junior debt and equity must reconcile.")
    if float(config.get("starting_cash", 0)) != 0:
        raise ValueError("Opening cash is unsupported; starting_cash must be zero.")
    if _date(config["legal_final_date"]) <= _date(config["as_of_date"]):
        raise ValueError("Legal final must follow the as-of date.")
    weights = scenario.get("default_weights", [1.0])
    if not weights or any(not math.isfinite(float(w)) or float(w) < 0 for w in weights):
        raise ValueError("Default timing weights must be nonnegative finite numbers.")
    if abs(sum(weights) - 1.0) > 1e-9:
        raise ValueError("Default timing weights must sum to one.")
    path = scenario.get("index_rate_path", config["index_rate_path"])
    if not path or any(not math.isfinite(float(r)) for r in path):
        raise ValueError("A nonempty finite index-rate path is required.")
    prepays = float(scenario.get("annual_prepayment_rate", config["annual_prepayment_rate"]))
    if not 0 <= prepays <= 1:
        raise ValueError("Annual prepayment rate must lie between zero and one.")
    if int(config["recovery_lag_quarters"]) != config["recovery_lag_quarters"] or config["recovery_lag_quarters"] < 0:
        raise ValueError("Recovery lag must be a nonnegative integer number of quarters.")
    if not 0 < float(config["reinvestment_price"]) <= 2:
        raise ValueError("Reinvestment price must be positive, in decimal price units.")
    for field in ("senior_coupon_bps", "junior_coupon_bps", "senior_fee_bps",
                  "subordinated_fee_bps", "fixed_fee_per_period", "oc_trigger", "ic_trigger"):
        if not math.isfinite(float(config[field])) or float(config[field]) < 0:
            raise ValueError(f"{field} must be a nonnegative finite value.")
    for field in ("final_liquidation_price", "oc_recovery_credit"):
        if not 0 <= float(config.get(field, 1 if field == "final_liquidation_price" else 0)) <= 1:
            raise ValueError(f"{field} must lie between zero and one.")
    if not 0 <= float(config["reinvestment_recovery"]) <= 1:
        raise ValueError("Reinvestment recovery must lie between zero and one.")
    if float(config["reinvestment_maturity_years"]) <= 0:
        raise ValueError("Reinvestment maturity must be positive.")
    if float(scenario.get("recovery_multiplier", 1)) < 0:
        raise ValueError("Recovery multiplier cannot be negative.")
    for f in facilities:
        for field in ("par", "recovery_aaa", "spread_bps", "fixed_coupon_rate", "floor_bps"):
            if f.get(field) is not None and not math.isfinite(float(f[field])):
                raise ValueError(f"Nonfinite {field} on {f.get('instrument_id')}.")
        if float(f["par"]) <= 0 or not 0 <= float(f["recovery_aaa"]) <= 1:
            raise ValueError("Facility par and recovery are out of range.")
        if f["rate_type"] not in ("Floating", "Fixed"):
            raise ValueError("Supported rate types are Floating and Fixed.")
        if int(f.get("payment_frequency", 4)) not in (2, 4):
            raise ValueError("Supported asset coupon frequencies are two or four per year.")
        if f["rate_type"] == "Floating" and (f.get("spread_bps") is None or f.get("floor_bps") is None):
            raise ValueError("Floating facilities require spread_bps and floor_bps.")
        if f["rate_type"] == "Fixed" and f.get("fixed_coupon_rate") is None:
            raise ValueError("Fixed facilities require a decimal fixed_coupon_rate.")
        if _date(f["maturity_date"]) <= _date(config["as_of_date"]):
            raise ValueError("Matured facilities require separate treatment and are unsupported.")
        if str(f.get("sp_rating", "")).upper() in ("CC", "C", "D", "SD", "NR"):
            raise ValueError("Already-defaulted facilities require separate treatment and are unsupported.")


def simulate(facilities: list[dict], config: dict, senior_pct: float,
             default_rate: float, scenario: dict) -> dict:
    """Return JSON-serializable summary, quarterly rows and independent checks.

    Period convention: default at period start, recovery at quarter end after the
    configured lag, prepayment/maturity at period end, and reinvestment after the
    interest waterfall. Asset interest accrues on post-default balances. Annual
    coupon frequencies of two and four are paid on a synthetic as-of-date anchor;
    semiannual coupons collect every second quarter. Prepayment/maturity collects
    the associated unpaid accrual. Defaults forfeit accrued unpaid interest.
    """
    _validate(facilities, config, senior_pct, default_rate, scenario)
    start, final = _date(config["as_of_date"]), _date(config["legal_final_date"])
    original = sum(float(f["par"]) for f in facilities)
    tolerance = max(0.01, original * 1e-10)
    equity_pct = float(config["equity_pct"])
    senior, junior = original * senior_pct, original * (1 - senior_pct - equity_pct)
    senior_arrears = junior_arrears = fee_arrears = sub_fee_arrears = 0.0
    carry_cash = carry_principal = carry_interest = cumulative_defaults = cumulative_recovery = 0.0
    total_equity = total_reinvest = missed_timely = 0.0
    recovery_schedule: dict[int, float] = {}
    weights = [float(v) for v in scenario.get("default_weights", [1.0])]
    curve = scenario.get("index_rate_path", config["index_rate_path"])
    prepay = float(scenario.get("annual_prepayment_rate", config["annual_prepayment_rate"]))
    recovery_multiplier = float(scenario.get("recovery_multiplier", 1.0))
    lag = int(config["recovery_lag_quarters"])
    reinvest_end = _date(config["reinvestment_end_date"])
    assets = []
    for f in facilities:
        assets.append({"balance": float(f["par"]), "maturity": _date(f["maturity_date"]),
                       "rate_type": f["rate_type"], "spread": float(f.get("spread_bps") or 0) / 10000,
                       "fixed": float(f.get("fixed_coupon_rate") or 0),
                       "floor": float(f.get("floor_bps") or 0) / 10000,
                       "recovery": min(1.0, float(f["recovery_aaa"]) * recovery_multiplier),
                       "frequency": int(f.get("payment_frequency", 4)), "accrued_interest": 0.0})
    periods = []
    previous = start
    n = 0
    while previous < final:
        n += 1
        end = min(_add_months(start, 3 * n), final)
        yf = (end - previous).days / 365.0
        index = _rate(curve, n - 1)
        opening = sum(a["balance"] for a in assets)
        opening_asset_interest = sum(a["accrued_interest"] for a in assets)
        senior_begin, junior_begin = senior, junior
        requested = original * default_rate * (weights[n - 1] if n <= len(weights) else 0)
        actual_defaults = min(opening, requested)
        fraction = actual_defaults / opening if opening else 0
        prepays = maturities = asset_interest = recoveries_created = 0.0
        asset_accrual = forfeited_interest = 0.0
        for a in assets:
            defaulted = a["balance"] * fraction
            a["balance"] -= defaulted
            forfeited_interest += a["accrued_interest"] * fraction
            a["accrued_interest"] *= 1 - fraction
            recoveries_created += defaulted * a["recovery"]
            maturity = a["maturity"]
            accrual = max(0, (min(end, maturity) - previous).days) / 365.0
            coupon = max(index, a["floor"]) + a["spread"] if a["rate_type"] == "Floating" else a["fixed"]
            earned = a["balance"] * max(0, coupon) * accrual
            asset_accrual += earned
            a["accrued_interest"] += earned
            if maturity <= end:
                maturities += a["balance"]
                a["balance"] = 0.0
                asset_interest += a["accrued_interest"]
                a["accrued_interest"] = 0.0
            else:
                prepay_fraction = 1 - (1 - prepay) ** yf
                paid = a["balance"] * prepay_fraction
                prepays += paid
                a["balance"] -= paid
                asset_interest += a["accrued_interest"] * prepay_fraction
                a["accrued_interest"] *= 1 - prepay_fraction
                if n % (4 // a["frequency"]) == 0 or end == final:
                    asset_interest += a["accrued_interest"]
                    a["accrued_interest"] = 0.0
        cumulative_defaults += actual_defaults
        recovery_schedule[n + lag] = recovery_schedule.get(n + lag, 0.0) + recoveries_created
        recovery_cash = recovery_schedule.pop(n, 0.0)
        cumulative_recovery += recovery_cash
        receivable = sum(recovery_schedule.values())
        liquidation = liquidated_par = 0.0
        if end == final:
            liquidated_par = sum(a["balance"] for a in assets)
            liquidation = liquidated_par * float(config.get("final_liquidation_price", 1.0))
            for a in assets:
                a["balance"] = 0.0
        principal_cash_begin, interest_cash_begin = carry_principal, carry_interest
        principal = carry_principal + prepays + maturities + recovery_cash + liquidation
        interest = carry_interest + asset_interest
        fees_due = fee_arrears + opening * float(config["senior_fee_bps"]) / 10000 * yf + float(config["fixed_fee_per_period"])
        fees_interest = min(interest, fees_due)
        interest -= fees_interest
        fees_principal = min(principal, fees_due - fees_interest) if config.get("principal_support_interest", True) else 0.0
        principal -= fees_principal
        fees_paid = fees_interest + fees_principal
        fee_arrears = max(0.0, fees_due - fees_paid)
        senior_current = senior * max(0, max(index, float(config.get("senior_floor_pct", 0))) + float(config["senior_coupon_bps"]) / 10000) * yf
        prior_senior_arrears = senior_arrears
        senior_due = senior_arrears + senior_current
        ic_numerator = interest
        ic_ratio = ic_numerator / senior_due if senior_due > tolerance else None
        senior_paid_i = min(interest, senior_due) if fee_arrears <= tolerance else 0.0
        interest -= senior_paid_i
        senior_paid_p = min(principal, senior_due - senior_paid_i) if config.get("principal_support_interest", True) and fee_arrears <= tolerance else 0.0
        principal -= senior_paid_p
        senior_paid = senior_paid_i + senior_paid_p
        senior_arrears = max(0.0, senior_due - senior_paid)
        senior_current_paid = max(0.0, senior_paid - prior_senior_arrears)
        current_missed = max(0.0, senior_current - senior_current_paid)
        missed_timely += current_missed
        collateral_for_oc = sum(a["balance"] for a in assets) + principal + receivable * float(config.get("oc_recovery_credit", 0.0))
        oc_ratio = collateral_for_oc / senior if senior > tolerance else None
        oc_triggered = oc_ratio is not None and oc_ratio < float(config["oc_trigger"])
        ic_triggered = ic_ratio is not None and ic_ratio < float(config["ic_trigger"])
        trigger = oc_triggered or ic_triggered
        diversion = min(interest, senior) if trigger else 0.0
        interest -= diversion
        senior -= diversion
        junior_current = junior * max(0, max(index, float(config.get("junior_floor_pct", 0))) + float(config["junior_coupon_bps"]) / 10000) * yf
        junior_due = junior_arrears + junior_current
        senior_obligations_clear = fee_arrears <= tolerance and senior_arrears <= tolerance
        # A failed test remains a distribution lockout for this payment period.
        junior_paid = min(interest, junior_due) if senior_obligations_clear and not trigger else 0.0
        interest -= junior_paid
        junior_arrears = max(0.0, junior_due - junior_paid)
        sub_due = sub_fee_arrears + opening * float(config["subordinated_fee_bps"]) / 10000 * yf
        sub_paid = min(interest, sub_due) if senior_obligations_clear and junior_arrears <= tolerance and not trigger else 0.0
        interest -= sub_paid
        sub_fee_arrears = max(0.0, sub_due - sub_paid)
        equity_i = interest if senior_obligations_clear and junior_arrears <= tolerance and sub_fee_arrears <= tolerance and not trigger else 0.0
        interest -= equity_i
        reinvest_cash = purchased = 0.0
        reinvest_allowed = end < reinvest_end and end < final and senior_obligations_clear
        if config.get("reinvestment_stop_on_trigger", True) and trigger:
            reinvest_allowed = False
        if reinvest_allowed:
            reinvest_cash = principal
            principal = 0.0
            purchased = reinvest_cash / float(config["reinvestment_price"])
            if purchased > tolerance:
                assets.append({"balance": purchased,
                               "maturity": _add_months(end, round(float(config["reinvestment_maturity_years"]) * 12)),
                               "rate_type": "Floating", "spread": float(config["reinvestment_spread_bps"]) / 10000,
                               "floor": float(config.get("reinvestment_floor_bps", 0)) / 10000, "fixed": 0.0,
                               "recovery": min(1.0, float(config["reinvestment_recovery"]) * recovery_multiplier),
                               "frequency": 4, "accrued_interest": 0.0})
        senior_paid_principal = min(principal, senior)
        principal -= senior_paid_principal
        senior -= senior_paid_principal
        junior_paid_principal = min(principal, junior) if senior <= tolerance and senior_obligations_clear else 0.0
        principal -= junior_paid_principal
        junior -= junior_paid_principal
        # Junior coupons may be settled from principal only after senior debt is
        # retired; this keeps unpaid junior interest from becoming equity cash.
        junior_paid_from_principal = min(principal, junior_arrears) if senior <= tolerance and senior_obligations_clear else 0.0
        principal -= junior_paid_from_principal
        junior_arrears -= junior_paid_from_principal
        junior_paid += junior_paid_from_principal
        sub_paid_from_principal = min(principal, sub_fee_arrears) if senior <= tolerance and junior <= tolerance and senior_obligations_clear and junior_arrears <= tolerance else 0.0
        principal -= sub_paid_from_principal
        sub_fee_arrears -= sub_paid_from_principal
        sub_paid += sub_paid_from_principal
        equity_p = principal if senior <= tolerance and junior <= tolerance and senior_obligations_clear and junior_arrears <= tolerance and sub_fee_arrears <= tolerance else 0.0
        principal -= equity_p
        carry_principal, carry_interest = max(0.0, principal), max(0.0, interest)
        carry_cash = carry_principal + carry_interest
        total_equity += equity_i + equity_p
        total_reinvest += reinvest_cash
        performing_end = sum(a["balance"] for a in assets)
        closing_asset_interest = sum(a["accrued_interest"] for a in assets)
        accrual_residual = opening_asset_interest + asset_accrual - forfeited_interest - asset_interest - closing_asset_interest
        sources = principal_cash_begin + interest_cash_begin + asset_interest + prepays + maturities + recovery_cash + liquidation
        uses = fees_paid + senior_paid + junior_paid + sub_paid + diversion + senior_paid_principal + junior_paid_principal + equity_i + equity_p + reinvest_cash + carry_cash
        cash_residual = sources - uses
        par_residual = opening - actual_defaults - prepays - maturities - liquidated_par + purchased - performing_end
        priority = 0.0
        if not senior_obligations_clear:
            priority += junior_paid + sub_paid + equity_i + junior_paid_principal + equity_p
        if senior > tolerance:
            priority += junior_paid_principal + equity_p
        if trigger:
            priority += equity_i
        row = {"period": n, "date": end.isoformat(), "year_fraction": yf, "index_rate": index,
               "performing_begin": opening, "requested_defaults": requested, "defaults": actual_defaults,
               "prepayments": prepays, "maturities": maturities, "liquidated_par": liquidated_par,
               "purchased_par": purchased, "performing_end": performing_end, "asset_interest": asset_interest,
               "asset_interest_accrued": asset_accrual, "asset_interest_forfeited": forfeited_interest,
               "asset_interest_receivable": closing_asset_interest,
               "asset_interest_accrual_residual": accrual_residual,
               "recoveries_created": recoveries_created, "recovery_cash": recovery_cash, "recovery_receivable": receivable,
               "liquidation_cash": liquidation, "principal_cash_begin": principal_cash_begin,
               "interest_cash_begin": interest_cash_begin,
               "senior_begin": senior_begin, "junior_begin": junior_begin,
               "senior_interest_current": senior_current, "senior_interest_due": senior_due,
               "senior_interest_paid": senior_paid, "senior_interest_shortfall": current_missed,
               "senior_interest_arrears": senior_arrears, "junior_interest_due": junior_due,
               "junior_interest_paid": junior_paid, "junior_interest_arrears": junior_arrears,
               "senior_fees_due": fees_due, "senior_fees_paid": fees_paid,
               "senior_fee_arrears": fee_arrears, "sub_fees_due": sub_due, "sub_fees_paid": sub_paid,
               "sub_fee_arrears": sub_fee_arrears, "oc_numerator": collateral_for_oc,
               "oc_denominator": senior_begin, "oc_ratio": oc_ratio, "ic_numerator": ic_numerator,
               "ic_denominator": senior_due, "ic_ratio": ic_ratio,
               "oc_triggered": oc_triggered, "ic_triggered": ic_triggered, "interest_diversion": diversion,
               "senior_principal_paid": senior_paid_principal + diversion,
               "junior_principal_paid": junior_paid_principal, "senior_end": senior, "junior_end": junior,
               "equity_interest": equity_i, "equity_principal": equity_p,
               "reinvestment_cash": reinvest_cash, "cash_end": carry_cash,
               "principal_cash_end": carry_principal, "interest_cash_end": carry_interest,
               "cash_residual": cash_residual, "par_residual": par_residual, "priority_violation": priority}
        periods.append(row)
        previous = end
    target_defaults = original * default_rate
    unallocated = max(0.0, target_defaults - cumulative_defaults)
    attained = unallocated <= tolerance
    max_cash = max(abs(p["cash_residual"]) for p in periods)
    max_par = max(abs(p["par_residual"]) for p in periods)
    max_priority = max(p["priority_violation"] for p in periods)
    max_accrual = max(abs(p["asset_interest_accrual_residual"]) for p in periods)
    minimum_balance = min(min(p[k] for k in ("performing_end", "senior_end", "junior_end", "cash_end")) for p in periods)
    # Receivable reconciliation includes amounts settling after legal final.
    receivable_residual = sum(p["recoveries_created"] for p in periods) - cumulative_recovery - sum(recovery_schedule.values())
    checks = [
        {"name": "Cash conservation", "passed": max_cash <= tolerance, "value": max_cash, "tolerance": tolerance},
        {"name": "Collateral par reconciliation", "passed": max_par <= tolerance, "value": max_par, "tolerance": tolerance},
        {"name": "Recovery receivable reconciliation", "passed": abs(receivable_residual) <= tolerance, "value": receivable_residual, "tolerance": tolerance},
        {"name": "Asset coupon accrual reconciliation", "passed": max_accrual <= tolerance, "value": max_accrual, "tolerance": tolerance},
        {"name": "Waterfall priority", "passed": max_priority <= tolerance, "value": max_priority, "tolerance": tolerance},
        {"name": "Nonnegative balances", "passed": minimum_balance >= -tolerance, "value": minimum_balance, "tolerance": tolerance},
        {"name": "Capital stack reconciliation", "passed": abs(senior_pct + (1-senior_pct-equity_pct) + equity_pct - 1) <= 1e-12, "value": senior_pct + (1-senior_pct-equity_pct) + equity_pct, "tolerance": 1e-12},
        {"name": "Target defaults attained", "passed": attained, "value": unallocated, "tolerance": tolerance},
    ]
    accounting_valid = all(c["passed"] for c in checks if c["name"] != "Target defaults attained")
    valid = accounting_valid and attained
    summary = {"scenario_id": str(scenario.get("id", "scenario")), "scenario_label": str(scenario.get("label", scenario.get("id", "Scenario"))),
               "senior_pct": senior_pct, "junior_pct": 1 - senior_pct - equity_pct, "equity_pct": equity_pct,
               "initial_par": original, "target_default_rate": default_rate,
               "realized_default_rate": cumulative_defaults / original, "default_target_attained": attained,
               "unallocated_defaults": unallocated, "senior_timely_interest_shortfall": missed_timely,
               "senior_interest_arrears": senior_arrears, "senior_principal_shortfall": max(0.0, senior),
               "junior_interest_arrears": junior_arrears, "junior_principal_shortfall": max(0.0, junior),
               "senior_fee_arrears": fee_arrears, "sub_fee_arrears": sub_fee_arrears,
               "equity_distributions": total_equity, "oc_breach_periods": sum(p["oc_triggered"] for p in periods),
               "ic_breach_periods": sum(p["ic_triggered"] for p in periods),
               "model_valid": valid, "accounting_valid": accounting_valid,
               "senior_pass": valid and missed_timely <= tolerance and senior <= tolerance and senior_arrears <= tolerance,
               "max_cash_residual": max_cash, "max_par_residual": max_par, "max_priority_violation": max_priority,
               "reinvested_cash": total_reinvest, "recovery_receivable_at_final": sum(recovery_schedule.values()),
               "cash_at_final": carry_cash, "stress_signature": _signature(facilities, config, scenario, default_rate),
               "method_status": "EXPLORATORY — not an agency rating or S&P model result"}
    return {"summary": summary, "periods": periods, "checks": checks}


def boundary_from_grid(rows: list[dict]) -> dict:
    """Describe the first grid failure without assuming a monotone waterfall."""
    rows = sorted(rows, key=lambda r: r["target_default_rate"])
    if not rows:
        return {"status": "NO TESTS", "lower_bound": None, "upper_bound": None, "non_monotonic": False}
    failures = [r for r in rows if r["default_target_attained"] and not r["senior_pass"]]
    first_fail = failures[0] if failures else None
    nonmonotonic = bool(first_fail and any(r["default_target_attained"] and r["senior_pass"] and r["target_default_rate"] > first_fail["target_default_rate"] for r in rows))
    any_infeasible = any(not r["default_target_attained"] for r in rows)
    if nonmonotonic:
        return {"status": "NON-MONOTONIC: inspect grid", "lower_bound": None,
                "upper_bound": None, "non_monotonic": True, "has_infeasible_targets": any_infeasible}
    if first_fail:
        prior = [r for r in rows if r["target_default_rate"] < first_fail["target_default_rate"]]
        passing = [r for r in prior if r["senior_pass"] and r["default_target_attained"]]
        if any(not r["default_target_attained"] for r in prior):
            return {"status": "UNATTAINABLE TARGETS: boundary unavailable", "lower_bound": None,
                    "upper_bound": None, "non_monotonic": False, "has_infeasible_targets": True}
        return {"status": "GRID BRACKET" if passing else "FAILS AT LOWEST TESTED RATE",
                "lower_bound": passing[-1]["target_default_rate"] if passing else None,
                "upper_bound": first_fail["target_default_rate"], "non_monotonic": False,
                "has_infeasible_targets": any_infeasible}
    passing = [r for r in rows if r["senior_pass"] and r["default_target_attained"]]
    return {"status": "UNATTAINABLE TARGETS: boundary unavailable" if any_infeasible else "NO FAILURE IN GRID",
            "lower_bound": None if any_infeasible or not passing else passing[-1]["target_default_rate"],
            "upper_bound": None, "non_monotonic": False, "has_infeasible_targets": any_infeasible}


def analyze(facilities: list[dict], config: dict) -> dict:
    """Run a fixed grid for each capital stack and retain one detailed base run."""
    scenarios = config["scenarios"]
    if not scenarios:
        raise ValueError("At least one explicitly configured scenario is required.")
    sizes = [float(v) for v in config["senior_sizes"]]
    base_size = float(config.get("base_senior_pct", 0.64))
    if base_size not in sizes:
        sizes = sorted(set(sizes + [base_size]))
    rates = sorted(set(float(v) for v in config["stress_default_rates"]))
    base_rate = float(config["base_default_rate"])
    base_scenario_id = config.get("base_scenario_id", scenarios[0]["id"])
    base_scenario = next((s for s in scenarios if s["id"] == base_scenario_id), None)
    if base_scenario is None:
        raise ValueError("base_scenario_id does not identify a configured scenario.")
    results, boundaries, sensitivity = [], [], []
    base_run = None
    for size in sizes:
        scenario_base = []
        size_boundaries = []
        for scenario in scenarios:
            series = []
            for severity in sorted(set(rates + [base_rate])):
                run = simulate(facilities, config, size, severity, scenario)
                record = run["summary"]
                results.append(record)
                if severity in rates:
                    series.append(record)
                if severity == base_rate:
                    scenario_base.append(record)
                    if size == base_size and scenario["id"] == base_scenario_id:
                        base_run = run
            boundary = boundary_from_grid(series)
            boundary.update({"senior_pct": size, "scenario_id": scenario["id"],
                             "label": "Exploratory first-failure default grid bracket"})
            boundaries.append(boundary)
            size_boundaries.append(boundary)
        # Invalid attainment is explicitly more restrictive than a numerical pass.
        binding = max(scenario_base, key=lambda r: (not r["model_valid"], not r["senior_pass"],
                      r["senior_principal_shortfall"], r["senior_timely_interest_shortfall"], r["unallocated_defaults"]))
        binding_basis = "Largest base-stress shortfall or unattained target; ties follow scenario order"
        binding_boundary = next(b for b in size_boundaries if b["scenario_id"] == binding["scenario_id"])
        if all(r["senior_pass"] for r in scenario_base):
            unresolved = [b for b in size_boundaries if b["non_monotonic"] or b["status"].startswith("UNATTAINABLE")]
            candidates = [b for b in size_boundaries if b["upper_bound"] is not None]
            if unresolved:
                binding_boundary = unresolved[0]
                binding_basis = "Boundary unresolved; inspect unattainable or non-monotonic scenario"
            elif candidates:
                binding_boundary = min(candidates, key=lambda b: (b["upper_bound"], b["lower_bound"] if b["lower_bound"] is not None else -1))
                binding_basis = "Lowest first-failure grid bracket; ties follow scenario order"
            else:
                binding_basis = "No failure in tested grid; no binding stress established"
        sensitivity.append({"senior_pct": size, "junior_pct": 1-size-float(config["equity_pct"]),
                            "equity_pct": float(config["equity_pct"]), "target_default_rate": base_rate,
                            "all_scenarios_valid": all(r["model_valid"] for r in scenario_base),
                            "all_scenarios_pass": all(r["senior_pass"] for r in scenario_base),
                            "binding_scenario": binding_boundary["scenario_id"],
                            "binding_basis": binding_basis,
                            "boundary_lower": binding_boundary["lower_bound"],
                            "boundary_upper": binding_boundary["upper_bound"],
                            "boundary_status": binding_boundary["status"],
                            "senior_principal_shortfall": max(r["senior_principal_shortfall"] for r in scenario_base),
                            "senior_timely_interest_shortfall": max(r["senior_timely_interest_shortfall"] for r in scenario_base),
                            "max_cash_residual": max(r["max_cash_residual"] for r in scenario_base)})
    return {"base_run": base_run, "stress_results": results, "sensitivities": sensitivity,
            "boundaries": boundaries, "scenarios": scenarios,
            "method_status": "Exploratory fixed-grid analysis; no proprietary SDR or agency BDR computed."}
