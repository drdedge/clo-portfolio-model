import csv
import math
import tempfile
import unittest
from pathlib import Path

from clo.fitch import (fitch_metrics, FITCH_FIELDS, FITCH_WARF_FACTORS,
                       FITCH_WARR_FACTORS)
from clo.inputs import ValidationError


def facility(iid, par, obligor=None):
    return {"instrument_id": iid, "obligor_id": obligor or iid, "par": par,
            "sp_rating": "AAA", "sp_industry": "Never copied", "recovery_aaa": .99}


def sidecar(iid, rating="B", recovery=.65):
    return {"instrument_id": iid, "fitch_idr": rating,
            "fitch_rating_basis": "reviewed_appendix5_equivalent",
            "fitch_industry": "", "fitch_recovery": recovery,
            "fitch_recovery_basis": "reviewed_bbsf_fallback", "source_reference": "Test fixture"}


class FitchTests(unittest.TestCase):
    def test_blank_template_retains_tables_without_numeric_metrics(self):
        result = fitch_metrics([])
        self.assertEqual(result["rows"], [])
        self.assertIsNone(result["warf"])
        self.assertIsNone(result["warr"])
        self.assertIsNone(result["coverage"]["rating_pct"])
        self.assertIsNone(result["coverage"]["recovery_pct"])
        self.assertIsNone(result["coverage"]["industry_pct"])
        self.assertEqual(result["factor_table"], FITCH_WARF_FACTORS)
        self.assertEqual(result["recovery_table"], FITCH_WARR_FACTORS)
        self.assertEqual(result["source"]["publication_date"], "2026-06-01")
        self.assertIn("NOT RUN", result["status"])

    def run_sidecar(self, portfolio, rows):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fitch.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, FITCH_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            return fitch_metrics(portfolio, path)

    def test_exact_published_factor_scale(self):
        self.assertEqual(list(FITCH_WARF_FACTORS.values()), [
            .136, .349, .629, .858, 1.237, 1.572, 2.099, 2.630, 3.162, 6.039,
            8.903, 11.844, 15.733, 19.627, 23.671, 32.221, 41.111, 50,
            63.431, 100, 100,
        ])
        self.assertEqual(FITCH_WARR_FACTORS["Group 1 - Strong"], .75)
        self.assertEqual(FITCH_WARR_FACTORS["Group 2 - Strong"], .65)
        self.assertEqual(FITCH_WARR_FACTORS["Group 3 - Weak"], .05)

    def test_no_silent_sp_substitution(self):
        result = fitch_metrics([facility("A", 100)])
        self.assertIsNone(result["warf"])
        self.assertIsNone(result["warr"])
        self.assertEqual(result["coverage"]["rating_pct"], 0)
        self.assertEqual(result["coverage"]["industry_pct"], 0)
        self.assertEqual(len(result["missing_inputs"]), 6)
        self.assertEqual(result["rows"][0]["fitch_industry"], "")

    def test_weighted_metrics_use_separate_fitch_inputs(self):
        result = self.run_sidecar([facility("A", 75), facility("B", 25)],
                                 [sidecar("A", "B", .75), sidecar("B", "BB", .65)])
        self.assertAlmostEqual(result["warf"], 20.71425)
        self.assertAlmostEqual(result["warr"], .725)
        self.assertEqual(result["coverage"]["rating_pct"], 1)
        self.assertIsNone(result["rdr"])
        self.assertIsNone(result["rlr"])
        self.assertEqual(len(result["source_hash"]), 64)

    def test_partial_coverage_does_not_report_biased_partial_average(self):
        a = sidecar("A")
        b = sidecar("B", "BB", "")
        result = self.run_sidecar([facility("A", 75), facility("B", 25)], [a, b])
        self.assertIsNotNone(result["warf"])
        self.assertIsNone(result["warr"])
        self.assertAlmostEqual(result["coverage"]["recovery_pct"], .75)
        partial = self.run_sidecar([facility("A", 75), facility("B", 25)], [a])
        self.assertIsNone(partial["warf"])
        self.assertAlmostEqual(partial["coverage"]["rating_pct"], .75)

    def test_assumptions_and_zero_recovery_are_explicit(self):
        row = sidecar("A", " b\u2212 ", 0)
        row["fitch_rating_basis"] = "development_proxy"
        row["fitch_recovery_basis"] = "development_assumption"
        result = self.run_sidecar([facility("A", 100)], [row])
        self.assertEqual(result["warf"], 32.221)
        self.assertEqual(result["warr"], 0)
        self.assertIn("development", result["warf_status"])
        self.assertIn("development", result["warr_status"])
        self.assertTrue(result["normalizations"])

    def test_invalid_data_and_ambiguous_ids_block(self):
        for rows in ([sidecar("A"), sidecar("A")], [sidecar("Z")],
                     [sidecar("A", "NR")], [sidecar("A", "D")],
                     [sidecar("A", recovery=65)], [sidecar("A", recovery=math.nan)]):
            with self.subTest(rows=rows), self.assertRaises(ValidationError):
                self.run_sidecar([facility("A", 100)], rows)
        with self.assertRaises(ValidationError):
            self.run_sidecar([facility("A", 50, "O"), facility("B", 50, "O")],
                             [sidecar("A", "B"), sidecar("B", "BB")])

    def test_missing_basis_and_source_block_metric_but_do_not_fill_values(self):
        for key in ("fitch_rating_basis", "source_reference"):
            row = sidecar("A")
            row[key] = ""
            result = self.run_sidecar([facility("A", 100)], [row])
            self.assertIsNone(result["warf"])
            self.assertTrue(any(gap["field"] == key for gap in result["missing_inputs"]))

    def test_facility_split_keeps_weighting_and_incompatible_industries_block(self):
        a = self.run_sidecar([facility("A", 100)], [sidecar("A")])
        b = self.run_sidecar([facility("A", 60, "O"), facility("B", 40, "O")],
                             [sidecar("A"), sidecar("B")])
        self.assertEqual(a["warf"], b["warf"])
        self.assertEqual(a["warr"], b["warr"])
        x, y = sidecar("A"), sidecar("B")
        x["fitch_industry"], y["fitch_industry"] = "X", "Y"
        with self.assertRaises(ValidationError):
            self.run_sidecar([facility("A", 60, "O"), facility("B", 40, "O")], [x, y])


if __name__ == "__main__":
    unittest.main()
