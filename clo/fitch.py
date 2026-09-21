"""Fitch public portfolio metrics; no PCM, rating default/loss rates or ratings.

Fitch inputs are supplied separately. No implicit S&P rating, industry or recovery
substitution is permitted. Missing inputs leave a whole-portfolio metric absent.
"""
from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path

from .inputs import ValidationError

FITCH_WARF_FACTORS = dict(zip(
    ("AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-",
     "BB+", "BB", "BB-", "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C"),
    (0.136, 0.349, 0.629, 0.858, 1.237, 1.572, 2.099, 2.630, 3.162, 6.039,
     8.903, 11.844, 15.733, 19.627, 23.671, 32.221, 41.111, 50.000, 63.431, 100.000, 100.000),
))
FITCH_WARR_FACTORS = {
    "Group 1 - DIP instrument": .95, "Group 1 - Strong": .75,
    "Group 1 - Senior secured bond": .60, "Group 1 - Moderate": .40,
    "Group 1 - Weak": .15, "Group 2 - Strong": .65,
    "Group 2 - Senior secured bond": .60, "Group 2 - Moderate": .40,
    "Group 2 - Weak": .15, "Group 3 - Strong": .30,
    "Group 3 - Moderate": .20, "Group 3 - Weak": .05,
}
FITCH_FIELDS = ("instrument_id", "fitch_idr", "fitch_rating_basis", "fitch_industry",
                "fitch_recovery", "fitch_recovery_basis", "source_reference")
RATING_BASES = ("public_fitch_idr", "reviewed_appendix5_equivalent", "development_proxy")
RECOVERY_BASES = ("fitch_issue_recovery_estimate", "fitch_issue_recovery_rating",
                  "reviewed_bbsf_fallback", "development_assumption")
FITCH_SOURCE = {
    "title": "CLOs and Corporate CDOs Rating Criteria",
    "publication_date": "2026-06-01", "verified_on": "2026-09-21",
    "url": "https://assets.fitchratings.com/downloadFile?reportType=report&sfReport=false&slug=structured-finance%2Fclos-corporate-cdos-rating-criteria-01-06-2026",
    "supplied_filename": "Fitch CLO Rating Criteria (06.01.2026) (2).pdf",
    "warf_reference": "Appendix 6 page 47; issuer-equivalency process Appendix 5 pages 45-46",
    "warr_reference": "Appendix 6 pages 47-48; fallback classification Appendix 4 pages 42-43",
    "warf_units": "Rating-factor points; numerical 10-year PCM asset default rate in percent",
    "warr_units": "Fraction, displayed as percent; issue recovery if available, otherwise BBsf fallback",
    "recovery_table_columns": ["Fitch recovery classification", "Recovery factor (fraction)"],
    "limitation": "Public arithmetic only. Rating assignments and recovery precedence require review. No PCM RDR, RRR, RLR or Fitch cash-flow test implemented.",
}


def _read_sidecar(path, known_ids):
    """Validate unambiguous row identity and supplied fields; blanks are gaps."""
    if path is None:
        return {}, [], None, None
    source_path = Path(path)
    issues, rows, changes = [], {}, []
    def issue(row, field, value, message):
        issues.append({"row": row, "field": field, "value": value, "message": message})
    with source_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        for header, count in Counter(headers).items():
            if count > 1:
                issue(1, header, header, "Duplicate Fitch sidecar column header")
        if "instrument_id" not in headers:
            issue(1, "instrument_id", None, "Fitch sidecar must contain instrument_id")
        for header in headers:
            if header not in FITCH_FIELDS:
                issue(1, header, header, "Unrecognized Fitch sidecar column; check spelling")
        if issues:
            raise ValidationError(issues)
        for number, raw in enumerate(reader, 2):
            if not any((value or "").strip() for key, value in raw.items() if key is not None):
                continue
            if None in raw:
                issue(number, "CSV", None, "Fitch sidecar row has more values than headers")
                continue
            row = {key: (raw.get(key) or "").strip() for key in FITCH_FIELDS}
            iid = row["instrument_id"]
            if not iid:
                issue(number, "instrument_id", iid, "Missing Fitch sidecar instrument identifier")
            elif iid not in known_ids:
                issue(number, "instrument_id", iid, "Fitch sidecar identifier not found in portfolio")
            elif iid in rows:
                issue(number, "instrument_id", iid, "Duplicate Fitch sidecar instrument identifier")
            rating = row["fitch_idr"].upper().replace("\u2212", "-")
            if rating != row["fitch_idr"]:
                changes.append({"row": number, "field": "fitch_idr", "from": row["fitch_idr"], "to": rating})
            row["fitch_idr"] = rating
            if rating and rating not in FITCH_WARF_FACTORS:
                issue(number, "fitch_idr", rating, "Unsupported Fitch IDR equivalency symbol; use reviewed AAA through C table value. NR/D/RD require separate treatment")
            if row["fitch_rating_basis"] and row["fitch_rating_basis"] not in RATING_BASES:
                issue(number, "fitch_rating_basis", row["fitch_rating_basis"], "Invalid Fitch rating basis")
            if row["fitch_recovery_basis"] and row["fitch_recovery_basis"] not in RECOVERY_BASES:
                issue(number, "fitch_recovery_basis", row["fitch_recovery_basis"], "Invalid Fitch recovery basis")
            recovery = row["fitch_recovery"]
            row["fitch_recovery"] = None
            if recovery:
                try:
                    value = float(recovery)
                    if not math.isfinite(value) or not 0 <= value <= 1:
                        raise ValueError
                    row["fitch_recovery"] = value
                except ValueError:
                    issue(number, "fitch_recovery", recovery, "Fitch recovery must be a finite fraction from 0 to 1; percentages such as 65 are invalid")
            rows[iid] = row
    if issues:
        raise ValidationError(issues)
    return rows, changes, str(source_path.resolve()), hashlib.sha256(source_path.read_bytes()).hexdigest()


def fitch_metrics(facilities, sidecar_path=None):
    """Return public WARF/WARR with separate input provenance and completeness.

    Fields missing from the optional sidecar remain missing; whole-portfolio WARF
    and WARR are available only at 100% coverage of their own required fields.
    Unverified industry labels never establish PCM or concentration-test coverage.
    """
    if not facilities:
        # A header-only template has no portfolio denominator. Retain lookup
        # metadata for the workbook, but never report zero risk or 0% coverage.
        if sidecar_path is not None:
            _, _, source_path, source_hash = _read_sidecar(sidecar_path, set())
        else:
            source_path, source_hash = None, None
        return {
            "warf": None, "warr": None, "warf_status": "NOT RUN - no portfolio",
            "warr_status": "NOT RUN - no portfolio", "status": "NOT RUN - no portfolio",
            "total_par": 0.0, "facility_count": 0, "rows": [],
            "coverage": {"rating_par": 0.0, "rating_pct": None,
                         "recovery_par": 0.0, "recovery_pct": None,
                         "industry_par": 0.0, "industry_pct": None,
                         "rating_assumed": False, "recovery_assumed": False},
            "industry_mapping_status": "NOT RUN - no portfolio",
            "missing_inputs": [], "normalizations": [], "source": FITCH_SOURCE.copy(),
            "factor_table": FITCH_WARF_FACTORS.copy(), "recovery_table": FITCH_WARR_FACTORS.copy(),
            "source_path": source_path, "source_hash": source_hash,
            "source_name": Path(source_path).name if source_path else None,
            "rdr": None, "rrr": None, "rlr": None, "rating_status": "NOT RUN - no portfolio",
        }
    ids = [row["instrument_id"] for row in facilities]
    if len(set(ids)) != len(ids) or any(not value for value in ids):
        raise ValueError("Fitch metrics require unique non-empty portfolio instrument identifiers")
    if any(not math.isfinite(float(row["par"])) or float(row["par"]) <= 0 for row in facilities):
        raise ValueError("Fitch metrics require positive finite portfolio par")
    sidecar, normalizations, source_path, source_hash = _read_sidecar(sidecar_path, set(ids))
    rows, gaps = [], []
    issuer_ratings, issuer_industries = defaultdict(set), defaultdict(set)
    for facility in facilities:
        iid, par = facility["instrument_id"], float(facility["par"])
        row = {key: "" for key in FITCH_FIELDS}
        row.update({"instrument_id": iid, "fitch_recovery": None})
        row.update(sidecar.get(iid, {}))
        row.update({"par": par, "obligor_id": facility["obligor_id"]})
        rating_ready = bool(row["fitch_idr"] and row["fitch_rating_basis"] and row["source_reference"])
        recovery_ready = bool(row["fitch_recovery"] is not None and row["fitch_recovery_basis"] and row["source_reference"])
        for field in ("fitch_idr", "fitch_rating_basis", "fitch_industry", "fitch_recovery", "fitch_recovery_basis", "source_reference"):
            if row[field] is None or row[field] == "":
                gaps.append({"instrument_id": iid, "field": field, "par": par, "message": "Missing separate Fitch input"})
        row["rating_factor"] = FITCH_WARF_FACTORS.get(row["fitch_idr"])
        row["rating_ready"], row["recovery_ready"] = rating_ready, recovery_ready
        row["rating_assumed"] = row["fitch_rating_basis"] == "development_proxy"
        row["recovery_assumed"] = row["fitch_recovery_basis"] == "development_assumption"
        row["defaulted_rating"] = row["fitch_idr"] in ("CC", "C")
        rows.append(row)
        if row["fitch_idr"]:
            issuer_ratings[row["obligor_id"]].add(row["fitch_idr"])
        if row["fitch_industry"]:
            issuer_industries[row["obligor_id"]].add(row["fitch_industry"])
    conflicts = [{"row": 0, "field": field, "value": oid,
                  "message": "Conflicting separate Fitch inputs across facilities of one obligor"}
                 for field, groups in (("fitch_idr", issuer_ratings), ("fitch_industry", issuer_industries))
                 for oid, values in groups.items() if len(values) > 1]
    if conflicts:
        raise ValidationError(conflicts)
    total = math.fsum(row["par"] for row in rows)
    rating_par = math.fsum(row["par"] for row in rows if row["rating_ready"])
    recovery_par = math.fsum(row["par"] for row in rows if row["recovery_ready"])
    industry_par = math.fsum(row["par"] for row in rows if row["fitch_industry"])
    ratings_complete = all(row["rating_ready"] for row in rows)
    recoveries_complete = all(row["recovery_ready"] for row in rows)
    rating_assumed = any(row["rating_assumed"] for row in rows)
    recovery_assumed = any(row["recovery_assumed"] for row in rows)
    def status(complete, assumed):
        return ("CALCULATED - development assumptions" if assumed else "CALCULATED - supplied reviewed input basis") if complete else "NOT CALCULATED - incomplete Fitch inputs"
    return {
        "warf": math.fsum(row["par"] * row["rating_factor"] for row in rows) / total if ratings_complete else None,
        "warr": math.fsum(row["par"] * row["fitch_recovery"] for row in rows) / total if recoveries_complete else None,
        "warf_status": status(ratings_complete, rating_assumed),
        "warr_status": status(recoveries_complete, recovery_assumed),
        "status": "PUBLIC METRICS ONLY - Fitch rating analysis incomplete",
        "total_par": total, "facility_count": len(rows), "rows": rows,
        "coverage": {"rating_par": rating_par, "rating_pct": rating_par / total,
                     "recovery_par": recovery_par, "recovery_pct": recovery_par / total,
                     "industry_par": industry_par, "industry_pct": industry_par / total,
                     "rating_assumed": rating_assumed, "recovery_assumed": recovery_assumed},
        "industry_mapping_status": "Supplied labels require Fitch taxonomy review" if industry_par else "NOT SUPPLIED - separate Fitch industry mapping required",
        "missing_inputs": gaps, "normalizations": normalizations,
        "source": FITCH_SOURCE.copy(), "factor_table": FITCH_WARF_FACTORS.copy(),
        "recovery_table": FITCH_WARR_FACTORS.copy(),
        "source_path": source_path, "source_hash": source_hash,
        "source_name": Path(source_path).name if source_path else None,
        "rdr": None, "rrr": None, "rlr": None,
        "rating_status": "NOT DETERMINED - PCM, Fitch stress/waterfall analysis and criteria review required",
    }
