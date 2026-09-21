"""Public S&P concentration stress arithmetic; no agency rating or SDR model.

Source: Global Methodology And Assumptions For CLOs And Corporate CDOs,
2019-06-21, republished 2026-04-10, table 4; paragraphs 59-65, 123, 156-164.
Inputs are normalized corporate exposures rated AAA through CCC-. The published
recovery rates used here are event-risk stresses, NOT facility recovery inputs.
"""
from __future__ import annotations

import math
from collections import defaultdict

SOURCE_META = {
    "title": "Global Methodology And Assumptions For CLOs And Corporate CDOs",
    "original_publication": "2019-06-21",
    "republication": "2026-04-10",
    "verified_on": "2026-09-21",
    "article_id": "3547721",
    "url": "https://www.spglobal.com/ratings/en/regulatory/article/-/view/sourceId/11020014",
    "evidence": "User-supplied 66-page PDF and current public S&P browser page agree",
    "status": "Public criteria components; not a CDO Evaluator reproduction or agency rating",
}
RATING_ORDER = (
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-",
    "BB+", "BB", "BB-", "B+", "B", "B-", "CCC+", "CCC", "CCC-",
)
# Published S&P rating factors, independently cross-checked to the issuer's
# November 2025 original filing. This is the performing CDO Monitor benchmark
# basis (CCC- or higher), not an agency scenario default rate or a rating.
SP_WARF_FACTORS = {
    "AAA": 13.51, "AA+": 26.75, "AA": 46.36, "AA-": 63.90,
    "A+": 99.50, "A": 146.35, "A-": 199.83, "BBB+": 271.01,
    "BBB": 361.17, "BBB-": 540.42, "BB+": 784.92, "BB": 1233.63,
    "BB-": 1565.44, "B+": 1982.00, "B": 2859.50, "B-": 3610.11,
    "CCC+": 4641.40, "CCC": 5293.00, "CCC-": 5751.10,
}
SP_WARF_EXCLUDED_RATINGS = ("CC", "C", "SD", "D")
SP_WARF_SOURCE = {
    "title": "SPWARF - published factor-table basis",
    "table_source_title": "Blue Owl Technology Finance Corp., Exhibit 10.1, S&P Rating Factor table, page 61",
    "table_source_url": "https://www.blueowltechnologyfinance.com/investors/sec-filings/all-sec-filings/content/0001193125-25-262653/d38473dex101.htm",
    "table_reference_date": "2025-11-03",
    "definition_source_title": "S&P Global Ratings, Presale: AUF Funding LLC, table 13 footnotes (i)-(ii)",
    "definition_source_url": "https://www.spglobal.com/ratings/en/regulatory/article/221215-presale-auf-funding-llc-s12592453",
    "definition_reference_date": "2022-12-15",
    "verified_on": "2026-09-21",
    "basis": "Par-weighted factors for ratings AAA through CCC-; below-CCC- assets excluded and disclosed",
    "status": "Published factor-table calculation, subject to rating-input and deal applicability review; not an agency rating or SDR",
    "limitation": "Factor table verified in an original issuer filing, not a current S&P licensed parameter release; no transaction-specific rating substitutions are imported",
}


def credit_quality_metrics(facilities):
    """Calculate the performing CDO Monitor benchmark SPWARF and dispersion.

    SPWARF = sum(par * factor) / eligible par. Dispersion is the par-weighted
    mean ABSOLUTE deviation from SPWARF, not a standard deviation. CC/C/SD/D
    are explicitly excluded from both denominators and their par is disclosed.
    NR, missing or unknown ratings fail instead of silently lowering the result.
    This helper does not enable defaulted collateral in the cash-flow engine.
    """
    if not facilities:
        raise ValueError("Cannot calculate SPWARF on an empty portfolio")
    details = []
    for index, row in enumerate(facilities, 1):
        rating = row.get("sp_rating")
        if rating not in SP_WARF_FACTORS and rating not in SP_WARF_EXCLUDED_RATINGS:
            raise ValueError(f"SPWARF requires an explicit supported S&P rating at row {index}: {rating!r}")
        try:
            par = float(row["par"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"SPWARF requires positive finite par at row {index}") from exc
        if not math.isfinite(par) or par <= 0:
            raise ValueError(f"SPWARF requires positive finite par at row {index}")
        included = rating in SP_WARF_FACTORS
        details.append({
            "instrument_id": row.get("instrument_id"), "row_number": index,
            "rating": rating, "par": par, "included": included,
            "rating_factor": SP_WARF_FACTORS.get(rating),
            "exclusion_reason": "" if included else "Below CCC-: excluded from performing benchmark",
        })
    eligible = [x for x in details if x["included"]]
    eligible_par = math.fsum(x["par"] for x in eligible)
    excluded_par = math.fsum(x["par"] for x in details if not x["included"])
    spwarf = (math.fsum(x["par"] * x["rating_factor"] for x in eligible) / eligible_par
              if eligible_par else None)
    dispersion = (math.fsum(x["par"] * abs(x["rating_factor"] - spwarf) for x in eligible)
                  / eligible_par if eligible_par else None)
    return {
        "spwarf": spwarf, "default_rate_dispersion": dispersion,
        "eligible_par": eligible_par, "excluded_par": excluded_par,
        "total_par": eligible_par + excluded_par,
        "eligible_facility_count": len(eligible),
        "excluded_facility_count": len(details) - len(eligible),
        "rating_factors": SP_WARF_FACTORS.copy(), "facility_factors": details,
        "source": SP_WARF_SOURCE.copy(), "basis": SP_WARF_SOURCE["basis"],
        "status": "CALCULATED - published factor-table basis" if eligible_par else "NOT CALCULATED - no eligible par",
    }


RATING_BANDS = ("AAA", "AA+", "A+", "BBB+", "BB+", "B+", "CCC+")
LIABILITY_CATEGORIES = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC")
# Rows correspond to RATING_BANDS; columns to LIABILITY_CATEGORIES. A zero is N/A.
OBLIGOR_DEFAULT_COUNTS = (
    (2, 1, 0, 0, 0, 0, 0),
    (3, 2, 1, 0, 0, 0, 0),
    (4, 3, 2, 1, 0, 0, 0),
    (6, 4, 3, 2, 1, 0, 0),
    (8, 6, 4, 3, 2, 1, 0),
    (10, 8, 6, 4, 3, 2, 1),
    (12, 10, 8, 6, 4, 3, 2),
)
ALTERNATIVE_INDUSTRY_COUNTS = {
    "AAA": (4, 6, 8, 12, 16, 20, 24),
    "AA": (2, 4, 6, 8, 12, 16, 20),
}
OBLIGOR_RECOVERY = 0.05
PRIMARY_INDUSTRY_RECOVERY = 0.17
ALTERNATIVE_INDUSTRY_RECOVERY = 0.05


def public_default_patterns(years=5):
    """Return fresh annual vectors as fractions of TOTAL cumulative defaults.

    Five-year vectors: table 20, typically for portfolio WAM of 4-7 years.
    Three-year vectors: table 21. Neither vector specifies cumulative defaults.
    The caller must select applicability and allocate annual amounts over dates.
    """
    raw = {
        5: ((39, 22, 16, 13, 10), (16, 23, 26, 22, 13),
            (12, 18, 22, 23, 25), (20, 20, 20, 20, 20)),
        3: ((50, 25, 25), (25, 50, 25), (25, 25, 50), (33, 33, 34)),
    }
    if years not in raw:
        raise ValueError("Only published three- and five-year default patterns are included")
    return {f"SP_pattern_{i}": [x / 100 for x in row]
            for i, row in enumerate(raw[years], 1)}


def _category(rating):
    if rating not in RATING_ORDER:
        raise ValueError(f"Unsupported target rating: {rating}")
    return rating.rstrip("+-")


def _aggregate(facilities):
    if not facilities:
        raise ValueError("Cannot run supplemental tests on an empty portfolio")
    groups = {}
    for row in facilities:
        oid = row["obligor_id"]
        rating, industry, par = row["sp_rating"], row["sp_industry"], float(row["par"])
        if not oid or not industry:
            raise ValueError("Obligor ID and S&P industry are required")
        if rating not in RATING_ORDER:
            raise ValueError("Supplemental tests require performing corporate ratings AAA-CCC-; "
                             "ratings below CCC- require the defaulted-asset treatment in paragraph 161")
        if not math.isfinite(par) or par <= 0:
            raise ValueError("Par must be finite and positive")
        if "sovereign" in str(row.get("seniority", "")).lower():
            raise ValueError("Sovereign supplemental recovery and industry exclusions are not implemented")
        if oid not in groups:
            groups[oid] = {"obligor_id": oid, "sp_rating": rating, "sp_industry": industry,
                           "par": 0.0, "facility_count": 0}
        group = groups[oid]
        if group["sp_rating"] != rating or group["sp_industry"] != industry:
            raise ValueError(f"Conflicting rating or industry for obligor {oid}")
        group["par"] += par
        group["facility_count"] += 1
    return sorted(groups.values(), key=lambda x: (-x["par"], x["obligor_id"]))


def _scenario(obligors, threshold, count, recovery, total, test, industry=None):
    eligible = [x for x in obligors if RATING_ORDER.index(x["sp_rating"]) >= RATING_ORDER.index(threshold)]
    chosen = sorted(eligible, key=lambda x: (-x["par"], x["obligor_id"]))[:count]
    gross = sum(x["par"] for x in chosen)
    loss = gross * (1 - recovery)
    return {"test": test, "rating_band": f"{threshold} through CCC-", "industry": industry,
            "required_obligor_count": count, "selected_obligor_count": len(chosen),
            "available_obligor_count": len(eligible), "selected_obligor_ids": [x["obligor_id"] for x in chosen],
            "gross_default_amount": gross, "gross_default_rate": gross / total,
            "recovery_rate": recovery, "net_loss_amount": loss, "net_loss_rate": loss / total}


def supplemental_tests(facilities, target_rating="AAA"):
    """Compute public event losses, with all scenarios retained for audit.

    Corporate scope only. Industry tests apply to AAA/AA. The published industry
    routes are alternatives: primary OR alternative, not their maximum. Both
    are reported. No amount here establishes tranche sufficiency: paragraph 56
    calls for cash-flow/payment analysis where excess spread is considered.
    """
    category = _category(target_rating)
    column = LIABILITY_CATEGORIES.index(category)
    obligors = _aggregate(facilities)
    total = sum(x["par"] for x in obligors)
    obligor_scenarios = [
        _scenario(obligors, band, counts[column], OBLIGOR_RECOVERY, total, "largest_obligor")
        for band, counts in zip(RATING_BANDS, OBLIGOR_DEFAULT_COUNTS) if counts[column]
    ]
    obligor_binding = max(obligor_scenarios, key=lambda x: x["net_loss_amount"])
    industry_groups = defaultdict(list)
    for row in obligors:
        industry_groups[row["sp_industry"]].append(row)
    primary_scenarios, alternative_scenarios = [], []
    if category in ALTERNATIVE_INDUSTRY_COUNTS:
        for industry, group in sorted(industry_groups.items()):
            primary_scenarios.append(_scenario(group, "AAA", len(group), PRIMARY_INDUSTRY_RECOVERY,
                                               total, "primary_industry", industry))
            alternative_scenarios.extend(
                _scenario(group, band, count, ALTERNATIVE_INDUSTRY_RECOVERY, total,
                          "alternative_industry", industry)
                for band, count in zip(RATING_BANDS, ALTERNATIVE_INDUSTRY_COUNTS[category])
            )
    primary = max(primary_scenarios, key=lambda x: x["net_loss_amount"]) if primary_scenarios else None
    alternative = max(alternative_scenarios, key=lambda x: x["net_loss_amount"]) if alternative_scenarios else None
    return {
        "source": SOURCE_META.copy(), "target_rating": target_rating,
        "liability_category": category, "total_par": total, "obligor_count": len(obligors),
        "largest_obligor": obligor_binding,
        "primary_industry": primary, "alternative_industry": alternative,
        "obligor_scenarios": obligor_scenarios,
        "primary_industry_scenarios": primary_scenarios,
        "alternative_industry_scenarios": alternative_scenarios,
        "industry_test_applicable": bool(primary_scenarios),
        "industry_route": "Primary OR alternative test" if primary_scenarios else "Not applicable below AA",
        "sufficiency_status": "NOT ASSESSED: event loss arithmetic only; deal cash-flow sufficiency review required",
        "scope": "Performing corporate exposures, supplied rating inputs and supplied industry mapping; no special-case overrides",
    }


# A public table lookup is available as a reference helper, but is deliberately
# not applied to portfolios automatically: precedence of recovery ratings, asset
# classification and country assignment require a reviewed input process.
RECOVERY_BY_TYPE_AND_GROUP = {
    "first_lien_non_covlite": {"A": (50, 55, 59, 63, 75, 79, 79), "B": (39, 42, 46, 49, 60, 63, 63), "C": (17, 19, 27, 29, 31, 34, 34)},
    "covlite_or_senior_secured_bond": {"A": (41, 46, 49, 53, 63, 67, 67), "B": (32, 35, 39, 41, 50, 53, 53), "C": (17, 19, 27, 29, 31, 34, 34)},
    "second_lien_or_unsecured": {"A": (18, 20, 23, 26, 29, 31, 31), "B": (13, 16, 18, 21, 23, 25, 25), "C": (10, 12, 14, 16, 18, 20, 20)},
    "subordinated": {"A": (8, 8, 8, 8, 8, 8, 8), "B": (8, 8, 8, 8, 8, 8, 8), "C": (5, 5, 5, 5, 5, 5, 5)},
}


def public_asset_type_recovery(asset_class, country_group, target_rating="AAA"):
    """Table 15 reference only; caller must establish that paragraphs 112-114 do not take precedence."""
    category = _category(target_rating)
    try:
        return RECOVERY_BY_TYPE_AND_GROUP[asset_class][country_group][LIABILITY_CATEGORIES.index(category)] / 100
    except KeyError as exc:
        raise ValueError("Explicit supported asset class and country group A/B/C required") from exc
