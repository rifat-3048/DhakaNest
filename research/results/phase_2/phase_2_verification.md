# Phase 2 Verification

## Completion status

Complete for the requested bounded critical review: 31 retained publications,
26 substantive full-text-section reviews, and coverage of all six themes.
Three retained publications are preprints and are labeled accordingly. Five
limited-access records do not contribute to the minimum 25. This does not claim
an exhaustive systematic review or independent replication of published results.

## Evidence package

The registry carries bibliographic identity, 30-column evidence fields in its
CSV view, evidence access, source sections, review status, critical analysis,
and actual RQ/hypothesis/comparison references. The bibliography, screening log,
matrix, and individual reviews are deterministic views of that evidence.

Forty deliberately logged records were screened: 31 included, four deferred,
five excluded as unrelated identifier mismatches. Counts are scoped to the log,
not the total number of web results. Bibliographic punctuation/accents are
transcribed in ASCII in the registry; versions are deduplicated by study and DOI.

## Checks performed

- Research unit suite: 24 tests passed, including ten new literature tests.
- Existing WSM/evaluation suites: 50 tests passed.
- Literature validator: passed for 31 identities, 26 substantive reviews,
  21 DOI entries checked for format/duplicates, all six categories, all eight
  hypotheses, consistent CSV views, and 31 valid BibTeX entries.
- New utilities/tests: Python compilation passed.
- Source JSON files: syntax checked as part of loading and validation.
- Git tracked diff: empty; only the existing untracked `research/` tree appears.
- Phase 0/1 and Phase 2 manifest checksums are checked during final sealing.

Commands from repository root:

```powershell
backend\.venv\Scripts\python.exe -m research.literature.validate_literature
backend\.venv\Scripts\python.exe -m unittest discover -s research\tests -v
backend\.venv\Scripts\python.exe -m py_compile research\literature\export_literature.py research\literature\validate_literature.py research\tests\test_literature.py
```

Backend regression command, from `backend/`:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_recommendation_part5 tests.test_recommendation_part7
```

## What validation means

Offline checks establish package consistency and reject dummy padding,
duplicates, missing analyses, unsupported access classes, bad references, and
unlabeled preprints. They do not verify every scientific claim automatically or
prove that a DOI resolved online. Bibliographic and source checks were performed
through the accessible sources listed in the registry. No subscription-database
coverage or comprehensive retraction audit is claimed.

## Remaining evidence limits

- P31's primary full text is a priority despite its verified author abstract.
- P09/P21 are bibliographic references; P08/P22 provide limited accessible text.
- P20's proceedings and contents are verified, but its review process was not
  independently verified.
- P28's landing-page and PDF author lists differ; the registry follows the PDF
  and records the discrepancy.
- P07 is an unreviewed manuscript with an internal reported-cost discrepancy
  between abstract and methods; its empirical claims remain author-reported.
- External draft references could not be reconciled verbatim because no local
  manuscript was found.
- Similar raw record counts between P20 and DhakaNest require provenance
  verification before independent-data claims.

## Non-regression and next boundary

All changes are new Phase 2 files under `research/`. Existing Phase 0/1 reports,
manifests, protocols, production code, model artifacts, datasets and historical
recommendations were preserved. No MongoDB/OSRM access, training, experiment,
human collection, package installation, or deployment occurred.

Phase 3 preparation should first resolve the controlled protocol-revision
recommendations in the comparative report: journey-aware baseline, explicit
single-destination control, separate location/constraint interventions, pooled
evaluation scope, and independent annotation anchoring. These are proposed
decisions, not authorized changes or completed experiments.
