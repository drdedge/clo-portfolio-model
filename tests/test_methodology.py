import unittest
from clo.methodology import (supplemental_tests, public_default_patterns, public_asset_type_recovery,
                             credit_quality_metrics, SP_WARF_FACTORS, SP_WARF_EXCLUDED_RATINGS)


def row(oid, par, rating="B", industry="Technology"):
    return {"obligor_id": oid, "par": par, "sp_rating": rating, "sp_industry": industry}


class MethodologyTests(unittest.TestCase):
    def test_multiple_facilities_are_one_obligor(self):
        result = supplemental_tests([row("A", 60, "AAA"), row("A", 40, "AAA"),
                                     row("B", 80, "AAA"), row("C", 70, "AAA")])
        self.assertEqual(result["obligor_count"], 3)
        self.assertEqual(result["largest_obligor"]["selected_obligor_ids"], ["A", "B"])
        self.assertAlmostEqual(result["largest_obligor"]["net_loss_amount"], 171)

    def test_rating_band_can_bind_above_top_two(self):
        rows = [row(str(i), 10, "B") for i in range(12)]
        result = supplemental_tests(rows)
        self.assertEqual(result["largest_obligor"]["required_obligor_count"], 10)
        self.assertAlmostEqual(result["largest_obligor"]["net_loss_amount"], 95)
        self.assertAlmostEqual(result["primary_industry"]["net_loss_amount"], 99.6)
        self.assertAlmostEqual(result["alternative_industry"]["net_loss_amount"], 114)

    def test_worst_rating_band_not_always_lowest(self):
        rows = [row("big1", 100, "AAA"), row("big2", 100, "AA"), row("small", 1, "CCC-")]
        result = supplemental_tests(rows)
        self.assertEqual(result["largest_obligor"]["rating_band"], "AAA through CCC-")
        self.assertAlmostEqual(result["largest_obligor"]["net_loss_amount"], 190)

    def test_alternative_can_be_less_than_primary(self):
        rows = [row(str(i), 10, "AAA") for i in range(10)]
        result = supplemental_tests(rows)
        self.assertAlmostEqual(result["primary_industry"]["net_loss_amount"], 83)
        self.assertAlmostEqual(result["alternative_industry"]["net_loss_amount"], 38)
        self.assertIn("OR", result["industry_route"])

    def test_rating_subcategory_uses_parent_test(self):
        rows = [row(str(i), 10, "B") for i in range(12)]
        self.assertEqual(supplemental_tests(rows, "AA-")["largest_obligor"],
                         supplemental_tests(rows, "AA")["largest_obligor"])
        self.assertFalse(supplemental_tests(rows, "A")["industry_test_applicable"])

    def test_defaulted_rating_and_conflicts_block(self):
        for bad in ("CC", "C", "SD", "D", "NR"):
            with self.assertRaises(ValueError): supplemental_tests([row("x", 100, bad)])
        with self.assertRaises(ValueError): supplemental_tests([row("x", 50), row("x", 50, "BB")])

    def test_vectors_and_recovery_reference(self):
        for years in (3, 5):
            for pattern in public_default_patterns(years).values():
                self.assertEqual(len(pattern), years)
                self.assertAlmostEqual(sum(pattern), 1)
        self.assertEqual(public_asset_type_recovery("first_lien_non_covlite", "A"), .50)
        self.assertEqual(public_asset_type_recovery("covlite_or_senior_secured_bond", "A"), .41)
        with self.assertRaises(ValueError): public_asset_type_recovery("loan", "unknown")

    def test_published_spwarf_scale_and_weighting(self):
        # Published issuer original table, 2025-11-03, p61: all 19 eligible
        # rating symbols and exact factors, including CCC- = 5751.10.
        self.assertEqual(list(SP_WARF_FACTORS.values()), [
            13.51, 26.75, 46.36, 63.90, 99.50, 146.35, 199.83, 271.01,
            361.17, 540.42, 784.92, 1233.63, 1565.44, 1982.00,
            2859.50, 3610.11, 4641.40, 5293.00, 5751.10,
        ])
        self.assertEqual(len(SP_WARF_FACTORS) + len(SP_WARF_EXCLUDED_RATINGS), 23)
        result = credit_quality_metrics([row("A", 75, "B"), row("B", 25, "BB")])
        self.assertAlmostEqual(result["spwarf"], 2453.0325)
        self.assertAlmostEqual(result["default_rate_dispersion"], 609.70125)
        self.assertEqual(result["eligible_par"], 100)
        self.assertEqual(result["excluded_par"], 0)

    def test_spwarf_facility_splits_and_scale_do_not_change_metric(self):
        original = credit_quality_metrics([row("A", 75, "B"), row("B", 25, "BB")])
        split = credit_quality_metrics([row("A", 300, "B"), row("A", 450, "B"), row("B", 250, "BB")])
        self.assertAlmostEqual(original["spwarf"], split["spwarf"])
        self.assertAlmostEqual(original["default_rate_dispersion"], split["default_rate_dispersion"])

    def test_spwarf_exclusions_have_matching_denominator(self):
        rows = [row("A", 100, "B")] + [row(r, 25, r) for r in ("CC", "C", "SD", "D")]
        result = credit_quality_metrics(rows)
        self.assertEqual(result["spwarf"], 2859.5)
        self.assertEqual(result["default_rate_dispersion"], 0)
        self.assertEqual(result["eligible_par"], 100)
        self.assertEqual(result["excluded_par"], 100)
        self.assertEqual(result["total_par"], 200)
        self.assertEqual(result["excluded_facility_count"], 4)
        self.assertTrue(all(x["rating_factor"] is None and x["exclusion_reason"]
                            for x in result["facility_factors"] if not x["included"]))
        empty_eligible = credit_quality_metrics([row("A", 100, "D")])
        self.assertIsNone(empty_eligible["spwarf"])
        self.assertIsNone(empty_eligible["default_rate_dispersion"])
        self.assertIn("no eligible par", empty_eligible["status"])

    def test_spwarf_invalid_values_cannot_disappear(self):
        for rating in (None, "", "NR", "foo", "b"):
            with self.subTest(rating=rating), self.assertRaises(ValueError):
                credit_quality_metrics([row("A", 50), row("B", 50, rating)])
        for par in (None, "x", 0, -1, float("nan"), float("inf")):
            with self.subTest(par=par), self.assertRaises(ValueError):
                credit_quality_metrics([row("A", par)])
        with self.assertRaises(ValueError):
            credit_quality_metrics([])


if __name__ == "__main__":
    unittest.main()
