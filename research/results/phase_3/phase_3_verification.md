# Phase 3 Verification

Classification: **partially complete**. Implemented and validated available-data
benchmark preparation; larger property snapshots, stored assessments and actual
OSRM evidence remain missing. No full-completion claim is made.

## Executed checks

- Research unit suite: 75 tests passed (24 existing, 51 new Phase 3).
- Relevant backend regressions: 96 tests passed across recommendation parts
  1, 2, 5 and 7 (hard filters, routing, WSM and budget v4).
- Dataset validation reconstructs all candidate records and annotation pools,
  verifies profiles/properties/coordinates, checks routing missingness, and
  validates the amendment without replacing Phase 1.
- Independent rebuild into a temporary new research directory is byte-identical
  for all dataset/configuration/manifest files.
- Python compilation checks cover new benchmark modules and tests.
- Prior Phase 0/1/2 manifest output checksums: 6 + 18 + 20 = 44 unchanged;
  their referenced dataset checksums are also verified.
- Dataset manifest binds 15 data files plus 16 production/protocol source inputs.
- Phase 3 experiment manifest binds all new source, test, amendment, report and
  dataset artifacts; the manifest does not recursively hash itself.
  The final authoritative seal is `phase_3_manifest_v2.json`. The original
  `phase_3_manifest.json` is retained as superseded first-pass metadata; its
  original output hashes are not a claim about the corrected current code.
- Git tracked diff is empty. All Phase 3 files remain inside research/; previous
  research files are preserved. No commit was requested or made.

Re-run commands and tool use are documented in `research/benchmark/README.md`.
Capture HTTP tests use mocked, temporary synthetic payloads only. No genuine
route times, predictions or human relevance judgments are asserted by them.

## Measured result

200 profiles, 12 fixture properties, 12 area destinations, 2,400 combinations,
860 unlabeled pool pairs, 144 missing OSRM pairs, 12 absent stored assessments.
Hard survivors: 40 profiles have 0, 88 have 1, 44 have 2, 28 have 3.
No profile has ten hard survivors; 160 profiles have unknown commute feasibility.
Sixty development/140 final profiles remain grouped by complete need family.

## Restrictions respected

No production code/formula/K/config/model changes. No MongoDB access or writes,
indexes, migrations, network routing, model inference/training, credential
disclosure, recommendation/history modification, frontend changes, installs,
server starts, deployment, Docker, human annotation, baselines, ablations, final
ranking evaluation or significance testing. Original phases remain checksum-bound.

## Required evidence before Phase 4

Obtain separately authorized, privacy-reviewed full listing documents and stored
assessments; identify real versus synthetic provenance and synthetic model-rent
circularity; verify appropriate precise geographic endpoints; authorize and
capture authentic routes; freeze a new version and repeat competition/pool
checks. Scenario expert review, ethics/annotation pilot and supervisor review
remain outstanding. Current files are suitable for preparation/testing, not
for commencing the intended independent human annotation or journal comparisons.
