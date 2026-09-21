# Separate Fitch inputs and public portfolio metrics

The optional Fitch CSV joins the normal portfolio by exact `instrument_id`. Use `templates/fitch_inputs_template.csv` and its accompanying dictionary. Omitting the file leaves Fitch metrics unavailable; the process never copies S&P inputs automatically.

The implemented reference is **Fitch, CLOs and Corporate CDOs Rating Criteria, June 1, 2026**, Appendix 6, pages 47-48 of the supplied PDF. [Fitch-hosted criteria PDF](https://assets.fitchratings.com/downloadFile?reportType=report&sfReport=false&slug=structured-finance%2Fclos-corporate-cdos-rating-criteria-01-06-2026).

## Fields

| Field | Required for | Meaning |
|---|---|---|
| instrument_id | Every supplied row | Exact matching portfolio facility ID |
| fitch_idr | WARF | Fitch IDR equivalency rating; Appendix 5 establishes the assignment hierarchy |
| fitch_rating_basis | WARF | `public_fitch_idr`, `reviewed_appendix5_equivalent`, or `development_proxy` |
| fitch_industry | Industry mapping | Separate Fitch label; may remain blank. Presence does not verify taxonomy compliance |
| fitch_recovery | WARR | Fraction from 0 to 1; `0.65` means 65%. Issue recovery estimate/rating-derived factor where available, otherwise BBsf fallback |
| fitch_recovery_basis | WARR | `fitch_issue_recovery_estimate`, `fitch_issue_recovery_rating`, `reviewed_bbsf_fallback`, or `development_assumption` |
| source_reference | WARF and WARR | Document, date and provenance for the supplied rating and recovery |

All fields except `instrument_id` can be absent or blank in a partial file. The relevant missing fields appear in the results. Whole-portfolio WARF or WARR requires complete coverage of its own input fields, basis and source reference. Partial averages are not presented as full-portfolio results. A recovery of zero is valid and differs from a missing recovery.

Unknown columns, duplicate identifiers/headers, unmatched identifiers, invalid ratings, recovery values outside [0,1], and conflicting issuer-level ratings or industries block processing with an explicit validation report. The supported factor table is AAA through C; D, RD and NR require separate treatment. CC and C have published factors of 100 and are marked as defaulted-rating inputs. The main cash-flow engine still does not support a defaulted collateral population.

## Calculations and their limits

- **Fitch WARF:** sum of facility par multiplied by the Appendix 6 rating factor, divided by total portfolio par. Factors follow Fitch's 10-year PCM asset-default scale in percentage-point units. They are numerically different from S&P factors and must not be compared as the same scale.
- **Fitch WARR:** sum of facility par multiplied by its separately supplied recovery factor, divided by total par. Issue recovery information takes precedence over fallback classification. This is the WARR benchmark basis; it is not a Fitch AAA rating recovery rate and must not be inserted into the S&P AAA recovery field.
- Industry inputs are held separately and their completeness is reported. The current implementation does not verify industry labels against a current PCM taxonomy or produce Fitch industry concentration tests.
- PCM **RDR**, **RRR**, **RLR**, Fitch cash-flow BDR and a Fitch rating conclusion remain unavailable. Neither complete metrics nor an assumed WARF closes those gaps.

## Fictional demonstration

`examples/fitch_example.csv` and `examples/fitch_replacement.csv` contain explicit development assumptions:

1. The S&P rating symbols are copied into the *separate sidecar* with `development_proxy` labels to exercise the workflow. This is not a Fitch rating or an implementation of Appendix 5's full hierarchy.
2. First-lien facilities are assumed to be senior secured loans, with no issue-specific recovery opinion available. Appendix 4 maps that category to Strong recovery; Appendix 6 supplies 75% for Group 1 and 65% for Group 2. Country memberships are taken from Appendix 4. These assumptions are recorded in each row's source reference.
3. Ambiguous seniority rows remain unfilled for recovery. Fitch industry labels remain blank pending a separate mapping.

For the 282-facility example, WARF is **21.42894853**, using assumed rating inputs. Recovery coverage is **98.5447% of par**, and the full WARR remains unavailable because seven facilities need classification or issue recovery information. This intentionally demonstrates an unresolved data requirement rather than manufacturing a complete result.

## Engine interface

`clo.fitch.fitch_metrics(facilities, sidecar_path=None)` returns WARF/WARR, separate status labels, input coverage, row-level inputs/factors, missing fields, factor tables, criteria metadata, normalization history, and the sidecar path/hash. It raises the package's `ValidationError` for malformed or ambiguous supplied data. Source references and review labels are declarations supplied by the user; the parser does not independently certify their provenance.

Changes to this CSV require a fresh engine run. The workbook's Fitch inputs are a review snapshot of these separate inputs.
