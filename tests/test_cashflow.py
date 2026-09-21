"""Independent accounting and boundary examples for the exploratory engine."""
import copy
import random
import unittest

from clo.cashflow import analyze, boundary_from_grid, simulate


def config():
    return {"as_of_date": "2027-01-01", "legal_final_date": "2029-01-01",
            "equity_pct": .10, "base_senior_pct": .64,
            "senior_coupon_bps": 0, "junior_coupon_bps": 0,
            "senior_fee_bps": 0, "fixed_fee_per_period": 0,
            "subordinated_fee_bps": 0, "oc_trigger": 0, "ic_trigger": 0,
            "recovery_lag_quarters": 0, "annual_prepayment_rate": 0,
            "reinvestment_end_date": "2027-01-01", "reinvestment_price": 1,
            "reinvestment_spread_bps": 400, "reinvestment_recovery": .4,
            "reinvestment_maturity_years": 1, "principal_support_interest": True,
            "index_rate_path": [0], "final_liquidation_price": 1,
            "senior_sizes": [.60, .64, .70], "stress_default_rates": [0, .5, 1],
            "base_default_rate": 0, "scenarios": [{"id": "early", "default_weights": [1]}]}


def facility(par=100, maturity="2028-01-01", frequency=4, coupon=0, recovery=.4):
    return {"instrument_id": "A", "obligor_id": "001", "obligor_name": "Example",
            "par": par, "sp_rating": "B", "sp_industry": "TEST", "country": "US",
            "seniority": "Senior Secured", "rate_type": "Fixed", "spread_bps": None,
            "fixed_coupon_rate": coupon, "floor_bps": None, "maturity_date": maturity,
            "recovery_aaa": recovery, "price": 1, "payment_frequency": frequency,
            "currency": "USD", "benchmark": "FIXED"}


class CashflowTests(unittest.TestCase):
    def run_case(self, severity=0, portfolio=None, cfg=None, scenario=None):
        return simulate(portfolio or [facility()], cfg or config(), .64, severity,
                        scenario or {"id": "test", "default_weights": [1]})

    def assert_reconciles(self, run):
        self.assertTrue(run["summary"]["accounting_valid"], run["checks"])
        for row in run["periods"]:
            self.assertAlmostEqual(row["cash_residual"], 0, places=7)
            self.assertAlmostEqual(row["par_residual"], 0, places=7)
            self.assertEqual(row["priority_violation"], 0)

    def test_zero_default_returns_debt_and_equity(self):
        run = self.run_case()
        self.assert_reconciles(run)
        self.assertTrue(run["summary"]["senior_pass"])
        self.assertAlmostEqual(sum(p["senior_principal_paid"] for p in run["periods"]), 64)
        self.assertAlmostEqual(sum(p["junior_principal_paid"] for p in run["periods"]), 26)
        self.assertAlmostEqual(run["summary"]["equity_distributions"], 10)

    def test_total_default_zero_recovery_has_no_phantom_cash(self):
        run = self.run_case(1, [facility(recovery=0)])
        self.assert_reconciles(run)
        self.assertFalse(run["summary"]["senior_pass"])
        self.assertAlmostEqual(run["summary"]["senior_principal_shortfall"], 64)
        self.assertEqual(run["summary"]["equity_distributions"], 0)

    def test_recovery_cash_arrives_once_after_lag(self):
        cfg = config()
        cfg["recovery_lag_quarters"] = 2
        run = self.run_case(1, cfg=cfg)
        self.assert_reconciles(run)
        self.assertEqual(run["periods"][0]["recovery_cash"], 0)
        self.assertEqual(run["periods"][1]["recovery_cash"], 0)
        self.assertAlmostEqual(run["periods"][2]["recovery_cash"], 40)
        self.assertAlmostEqual(sum(p["recovery_cash"] for p in run["periods"]), 40)

    def test_recovery_after_final_is_not_available(self):
        cfg = config()
        cfg["recovery_lag_quarters"] = 20
        run = self.run_case(1, [facility(recovery=1)], cfg)
        self.assert_reconciles(run)
        self.assertEqual(run["summary"]["recovery_receivable_at_final"], 100)
        self.assertEqual(run["summary"]["senior_principal_shortfall"], 64)

    def test_late_default_target_is_infeasible(self):
        run = self.run_case(.5, scenario={"id": "late", "default_weights": [0, 0, 0, 0, 1]})
        self.assertTrue(run["summary"]["accounting_valid"])
        self.assertFalse(run["summary"]["default_target_attained"])
        self.assertFalse(run["summary"]["senior_pass"])
        self.assertEqual(run["summary"]["unallocated_defaults"], 50)

    def test_prepayment_and_maturity_do_not_double_count(self):
        cfg = config()
        cfg["annual_prepayment_rate"] = 1
        run = self.run_case(.2, cfg=cfg)
        self.assert_reconciles(run)
        self.assertAlmostEqual(sum(p["prepayments"] + p["maturities"] for p in run["periods"]), 80)
        self.assertAlmostEqual(sum(p["defaults"] for p in run["periods"]), 20)

    def test_semiannual_interest_collects_on_second_quarter(self):
        run = self.run_case(portfolio=[facility(frequency=2, coupon=.10)])
        self.assert_reconciles(run)
        self.assertEqual(run["periods"][0]["asset_interest"], 0)
        self.assertGreater(run["periods"][0]["asset_interest_receivable"], 0)
        self.assertAlmostEqual(run["periods"][1]["asset_interest"], 100*.1*181/365)
        self.assertAlmostEqual(sum(p["asset_interest"] for p in run["periods"]), 10)

    def test_default_forfeits_unpaid_coupon(self):
        run = self.run_case(.5, [facility(frequency=2, coupon=.1)],
                            scenario={"id": "second", "default_weights": [0, 1]})
        self.assert_reconciles(run)
        self.assertAlmostEqual(run["periods"][1]["asset_interest_forfeited"], 100*.1*90/365*.5)
        self.assertAlmostEqual(run["periods"][1]["asset_interest"], 50*.1*181/365)

    def test_cured_interest_shortfall_still_fails_timeliness(self):
        cfg = config()
        cfg["senior_coupon_bps"] = 200
        cfg["principal_support_interest"] = False
        run = self.run_case(portfolio=[facility(frequency=2, coupon=.2)], cfg=cfg)
        self.assert_reconciles(run)
        self.assertGreater(run["summary"]["senior_timely_interest_shortfall"], 0)
        self.assertEqual(run["summary"]["senior_interest_arrears"], 0)
        self.assertFalse(run["summary"]["senior_pass"])

    def test_principal_support_can_pay_senior_interest(self):
        cfg = config()
        cfg["senior_coupon_bps"] = 100
        cfg["annual_prepayment_rate"] = .5
        run = self.run_case(cfg=cfg)
        self.assert_reconciles(run)
        self.assertEqual(run["summary"]["senior_timely_interest_shortfall"], 0)

    def test_coverage_trigger_diverts_interest(self):
        cfg = config()
        cfg["oc_trigger"] = 2
        run = self.run_case(portfolio=[facility(coupon=.10)], cfg=cfg)
        self.assert_reconciles(run)
        first = run["periods"][0]
        self.assertTrue(first["oc_triggered"])
        self.assertEqual(first["equity_interest"], 0)
        self.assertAlmostEqual(first["interest_diversion"], first["asset_interest"])

    def test_ic_trigger_uses_pre_coupon_interest(self):
        cfg = config()
        cfg["senior_coupon_bps"] = 100
        cfg["ic_trigger"] = 2
        run = self.run_case(portfolio=[facility(coupon=.01)], cfg=cfg)
        first = run["periods"][0]
        self.assertAlmostEqual(first["ic_ratio"], 1 / .64)
        self.assertTrue(first["ic_triggered"])

    def test_reinvestment_cash_is_not_double_spent(self):
        cfg = config()
        cfg["annual_prepayment_rate"] = .3
        cfg["reinvestment_end_date"] = "2028-01-01"
        cfg["reinvestment_price"] = .8
        run = self.run_case(cfg=cfg)
        self.assert_reconciles(run)
        first = run["periods"][0]
        self.assertGreater(first["reinvestment_cash"], 0)
        self.assertEqual(first["senior_principal_paid"], 0)
        self.assertAlmostEqual(first["purchased_par"], first["reinvestment_cash"]/.8)

    def test_fees_retain_priority_and_unpaid_fees_do_not_disappear(self):
        cfg = config()
        cfg["fixed_fee_per_period"] = 30
        run = self.run_case(cfg=cfg)
        self.assert_reconciles(run)
        self.assertEqual(sum(p["junior_interest_paid"] for p in run["periods"]), 0)
        self.assertEqual(run["summary"]["equity_distributions"], 0)
        self.assertGreater(run["summary"]["senior_fee_arrears"], 0)

    def test_grid_nonmonotonicity_is_reported(self):
        rows = [{"target_default_rate": d, "default_target_attained": True, "senior_pass": p}
                for d, p in [(0, True), (.5, False), (1, True)]]
        boundary = boundary_from_grid(rows)
        self.assertTrue(boundary["non_monotonic"])
        self.assertIsNone(boundary["lower_bound"])

    def test_grid_bracket_and_infeasibility(self):
        rows = [{"target_default_rate": d, "default_target_attained": True, "senior_pass": p}
                for d, p in [(0, True), (.5, True), (1, False)]]
        result = boundary_from_grid(rows)
        self.assertEqual(result["lower_bound"], .5)
        self.assertEqual(result["upper_bound"], 1)
        rows[1]["default_target_attained"] = False
        self.assertIn("UNATTAINABLE", boundary_from_grid(rows)["status"])

    def test_capital_sensitivity_uses_identical_stress_inputs(self):
        run = analyze([facility()], config())
        self.assertEqual(len(run["sensitivities"]), 3)
        for severity in (0, .5, 1):
            records = [r for r in run["stress_results"] if r["target_default_rate"] == severity]
            self.assertEqual(len({r["stress_signature"] for r in records}), 1)
            for record in records:
                self.assertAlmostEqual(record["senior_pct"]+record["junior_pct"]+record["equity_pct"], 1)

    def test_bad_inputs_fail_explicitly(self):
        for field, value in [("rate_type", "Unknown"), ("recovery_aaa", 1.2), ("payment_frequency", 12)]:
            f = facility()
            f[field] = value
            with self.assertRaises(ValueError):
                self.run_case(portfolio=[f])
        with self.assertRaises(ValueError):
            self.run_case(scenario={"default_weights": [.4, .4]})

    def test_negative_benchmark_never_creates_negative_note_coupons(self):
        cfg = config()
        cfg["index_rate_path"] = [-.05]
        cfg["senior_floor_pct"] = -.10
        cfg["junior_floor_pct"] = -.10
        run = self.run_case(cfg=cfg)
        self.assert_reconciles(run)
        self.assertEqual(sum(p["senior_interest_due"] for p in run["periods"]), 0)
        self.assertEqual(sum(p["junior_interest_due"] for p in run["periods"]), 0)

    def test_interest_and_principal_cash_carry_remain_separate(self):
        cfg = config()
        cfg["oc_trigger"] = 100
        # Coupon exceeds senior principal; trigger traps residual interest for
        # one period and it remains in the interest account on the next date.
        run = self.run_case(portfolio=[facility(coupon=4)], cfg=cfg)
        self.assert_reconciles(run)
        self.assertGreater(run["periods"][0]["interest_cash_end"], 0)
        self.assertEqual(run["periods"][1]["interest_cash_begin"], run["periods"][0]["interest_cash_end"])
        self.assertEqual(run["periods"][1]["principal_cash_begin"], 0)

    def test_oc_threshold_equality_passes_and_higher_threshold_triggers(self):
        cfg = config()
        cfg["oc_trigger"] = 100/64
        run = self.run_case(cfg=cfg)
        self.assertFalse(run["periods"][0]["oc_triggered"])
        cfg["oc_trigger"] += .0001
        run = self.run_case(cfg=cfg)
        self.assertTrue(run["periods"][0]["oc_triggered"])

    def test_seeded_mixed_waterfalls_conserve_cash_and_priority(self):
        rng = random.Random(742)
        for _ in range(20):
            cfg = config()
            cfg.update({"senior_coupon_bps": rng.uniform(0, 500),
                        "junior_coupon_bps": rng.uniform(0, 1000),
                        "senior_fee_bps": rng.uniform(0, 100),
                        "subordinated_fee_bps": rng.uniform(0, 100),
                        "fixed_fee_per_period": rng.uniform(0, 3),
                        "annual_prepayment_rate": rng.uniform(0, .9),
                        "oc_trigger": rng.uniform(1, 2), "ic_trigger": rng.uniform(.5, 2),
                        "principal_support_interest": rng.choice([False, True]),
                        "reinvestment_end_date": rng.choice(["2027-01-01", "2028-01-01"]),
                        "recovery_lag_quarters": rng.randint(0, 10)})
            assets = [facility(par=50, coupon=rng.uniform(0, .2), frequency=2),
                      facility(par=50, coupon=rng.uniform(0, .2), frequency=4)]
            run = self.run_case(rng.random(), assets, cfg,
                                {"id": "mixed", "default_weights": [.2, .4, .1, .3]})
            self.assert_reconciles(run)


if __name__ == "__main__":
    unittest.main()
