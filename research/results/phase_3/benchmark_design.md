# Phase 3 Benchmark Design

Status: **partially complete**. This phase implements working preparation tools
and freezes the available evidence, not a completed recommendation experiment.
No KNN/WSM ranking, baseline, ablation, human annotation, metric evaluation,
model inference, MongoDB access, or live routing was executed.

## Implemented inputs

- 200 distinct, schema-valid synthetic tenant scenarios: ten substantive need
  families, five need conditions, four geographic contexts; 20 profiles/family.
- Families cover students, professionals, children/family housing, healthcare
  access, multiple workers, constrained/flexible budgets, strict commuting,
  space/amenities, and rent reasonableness. These are constructed scenarios,
  not sensitive attributes inferred about people or expert-validated elicitation.
- 12 statically reconstructed repository seed properties, classified as
  **evaluation_fixture**, not real observations or snapshots of MongoDB.
- 12 existing area-anchor destinations, no invented institution coordinates.
- 144 explicit missing-route records in JSONL, never fabricated OSRM values.
- 860 independent, unlabeled tenant-property annotation pairs and a separate
  blinded view. Internal nomination records are not annotator-facing.

Source extraction parses literal AST nodes from the original seed script. It
does not import that script, connect its database client, or call its model.
Fixture status approved/available is an explicit construction assumption;
available-from uses fixed base date 2026-10-25 plus the existing seed offsets.
Those assumptions are not evidence of current real-world availability.

The existing academic generator creates 2,500 active and 100 lifecycle records
through model calls, model-linked rent multipliers, and coordinate jitter. Its
aggregate report cannot recover exact stored documents/assessments. Neither new
predictions nor invented jitter are substituted for missing snapshots. The
export specification and offline importer support separately authorized recovery.

## Protocol and partitions

Effective version 1.1.0-phase3 references untouched Phase 1 version 1.0.0 plus
the explicit four-part amendment. User implementation authorization is recorded;
supervisor approval is **not** recorded. Journey-inspired and single-destination
comparisons are specified, not implemented. See the amendment for blinding,
common pools, and controlled versus end-to-end candidate comparisons.

Seed 42 shuffles entire scenario families: 60 development and 140 final profiles.
Related variants cannot cross folds. This holds whole need families out and is
therefore a scenario-transfer design, not an IID split or geographic holdout.
Inventory and area anchors are shared; no real-market generalization follows.
No final labels or ranked outcomes were generated or inspected.

Data generation refuses an existing output directory. All data/configuration
contents reproduce byte-for-byte into a new directory. Dataset and experiment
manifests bind input sources and outputs; experiment timestamps naturally vary.
