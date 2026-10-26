# Search and Screening Report

Search date: 2026-10-25. Protocol: `research/literature/search_protocol.json`.

## Search scope

This is a structured critical review with deliberate coverage of six research
themes, supplemented by backward references. It is not an exhaustive systematic
review or a claim that all relevant publications were found. Public scholarly
web discovery, publisher pages, arXiv, university/author repositories, NeurIPS,
MLSys, and bibliographic records were actually used. Google Scholar, Scopus,
Web of Science, and subscription database search interfaces were not searched.
Publisher DOI pages that returned 403/429, timeout, or oversized-file errors are
recorded as access limitations rather than evidence of paper contents.

Searches covered property recommendations, journey-aware housing, geographical
recommendation, MCDM, rent estimation, boosting, explanation, evaluation, and
uncertainty. The exact executed query subset and inclusion/exclusion rules are
in the JSON protocol. Backward tracing from P02 identified P31, a particularly
important journey-aware predecessor. P04 led to the original HomeFinder (P05).

## Bounded screening counts

| Item | Count |
|---|---:|
| Deliberately recorded discovery/screening records | 40 |
| Retained unique publications | 31 |
| Full-text section reviews | 26 |
| Abstract and metadata reviews | 3 |
| Metadata-only references | 2 |
| Deferred leads | 4 |
| Excluded identifier mismatches/unrelated papers | 5 |

These are record-level decisions in `screening_log.csv`, not raw search-engine
hit counts. Repeated retrievals, arXiv/publisher copies, and conference/journal
versions of the same underlying study were not counted twice. The retained set
includes three clearly identified preprints (P06, P07, P24). The IEOM paper P20
has verified proceedings/content but an independently unverified review process.

All six categories A-F are represented. Full-text access means methods,
evaluation, and discussion sections were available and examined where relevant;
it does not imply a line-by-line reading of every appendix. Each registry entry
identifies the evidence location. Missing detail remains marked rather than
filled from another paper or model memory.

## Existing-reference reconciliation

| Reference family named in the brief | Resolution |
|---|---|
| RE-RecSys | P01: original title, authors, conference DOI and full text verified |
| Real-estate systematic review | P02 full text; P08 publisher abstract only; exact draft choice unknown |
| General recommender review | P13 provides verified hybrid-review coverage; exact original reference not recoverable locally |
| Earlier Dhaka rent estimation | S32 identified and deferred pending venue/data audit; not counted |
| Explainable Dhaka rent prediction | P20 proceedings PDF and index verified |
| OSRM research | P09 bibliographic identity verified; primary full text unavailable |
| Original XGBoost | P14 author manuscript and official project citation verified |

No local manuscript/reference list was located in `docs/` or `research/`.
Consequently this is a reference-family reconciliation, not a claim that the
external draft's exact seven citations were read or corrected.

## Limits and follow-up

Priority retrievals are P31's full methods/user study and P09's original text.
P08 and P22 remain limited-access background. The 2026 domain review S33 and
the explainable survey S34 should be reviewed in a future supplement. No paid
credentials or private manuscript was accessed. No retraction notice was seen;
a comprehensive retraction/Crossmark audit was not available and is not claimed.

The 31-paper registry is a frozen selection with explicit uncertainty. It does
not justify universal novelty or exhaustive-coverage claims.
