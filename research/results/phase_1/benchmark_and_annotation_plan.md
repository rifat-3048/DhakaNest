# Benchmark and Annotation Plan

## Future benchmark

The initial journal benchmark target is 100-300 tenant profiles. This is a
planning range, not an existing sample. Profiles should cover Dhaka regions,
budgets, household/property needs, and one-, two-, and three-destination cases
with varied importance and commute limits.

Profiles may come from consented, de-identified preference elicitation and
expert-constructed coverage scenarios. Each receives a `source_type`; synthetic
profiles and properties remain distinguishable from real observations in every
analysis. Profile facts, including a conventional area-first neighborhood, are
frozen before method output or labels are viewed.

Each property snapshot records source/provenance, observation time, approval
and availability state, canonical fields, valid coordinates, rent assessment,
and checksum. Quality checks cover schema validity, positive numeric values,
coordinates, canonical categories, and completeness. Exact duplicates are
removed by canonical fingerprint. Near-duplicates are clustered using location,
rent, size, rooms, text, and image hashes so copies do not cross partitions or
inflate evaluation.

For every profile-property pair, freeze OSRM duration and distance matrices,
unreachable cells, request coordinates, profile, retrieval time, engine/base
data information when available, and SHA-256. Evaluation never calls live
routing.

Use a grouped, stratified 30% development and 70% final-evaluation split. Keep
related profile families and near-duplicate property clusters together. Seal
final labels until methods, exclusions, metrics, and code are frozen.

## Candidate pool and workload

Full-universe annotation is likely impractical. Build a blinded pool per
profile from the deduplicated union of top candidates from every method,
seeded-random eligible candidates, and prespecified hard negatives. A pilot
should determine the final pool size; approximately 20-30 properties per
profile is an expectation for planning, not a completed design result.

Record each item's pool source and the unjudged rate. Never treat an unjudged
property as relevance zero. Profiles without enough eligible competition remain
useful for coverage analysis but should be flagged for ranking evaluation.

## Independent annotation

Annotators must be adults, understand the profile language, and be familiar
with Dhaka renting or housing decisions. They disclose real-estate expertise,
project relationships, and profile-construction involvement. Profile authors
cannot judge their own profiles.

At least three independent valid annotators judge every pooled profile-property
pair. They see tenant needs, property facts, frozen per-destination route
time/distance, rent versus budget, and separately labeled estimated travel/total
spending. They do not see algorithm identity, rank, KNN similarity, WSM scores,
final suitability, explanations, or other labels. Property order is randomized
with recorded seeds.

| Label | Meaning | Example |
|---|---|---|
| 0 | Not suitable or violates a mandatory need | Over a no-flexibility budget or beyond a required commute |
| 1 | Marginal; substantial compromises | Eligible but poor on important journeys and desired features |
| 2 | Suitable with acceptable compromises | Meets mandatory needs with moderate soft tradeoffs |
| 3 | Highly suitable with minor compromises | Strong on the profile's important housing and commute needs |

Training uses excluded practice items and written rationales. Quality controls
include attention checks, repeated-item consistency, timing flags, and
mandatory-rule comprehension. Exclusion rules are frozen before labels are
aggregated.

Ordinal Krippendorff alpha is the primary multi-rater agreement statistic;
quadratic-weighted pairwise Cohen kappa supports two-rater diagnostics. The
initial consensus label is the median of at least three valid ratings. A rating
range of two or more, missing stable median, or mandatory-rule disagreement
triggers blinded senior adjudication. Preserve every raw label, rationale,
exclusion, and adjudication outcome.

Human collection requires applicable institutional ethics review, consent,
data minimization, withdrawal procedures, controlled access, and retention
rules. Phase 1 creates no profiles, properties, labels, or participant data.
