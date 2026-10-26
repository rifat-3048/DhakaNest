# Annotation Pool Report

The initial pool has **860 unique tenant-property pairs**: 3-6 per profile,
median 4. Counts by pool size: 3=>40, 4=>88, 5=>44, 6=>28 profiles. The target
of 24 per profile is not achieved because only twelve fixtures exist and few
survive each request. No relevance labels were produced.

Selection is seeded and independent of KNN/WSM outcomes: cover eligible type,
area and rent strata, random eligible candidates, rent-boundary candidates,
structural variety, and up to three nearest-rent excluded cases. Excluded cases
are explicitly recorded internally as hard-filter negatives, not assigned human
labels. If authentic routes are present, the framework can nominate verified
commute-compatible/incompatible cases. That diversity has not been achieved in
the present missing-route dataset. Future algorithm nominations can be merged
by tenant-property key, without duplicate pairs or carrying ranks into exports.

`annotation_pool.json` is internal and contains sampling provenance. The
separate `annotation_blinded_export.json` includes opaque pair IDs, requirements,
structural home facts, coordinate precision, and commute evidence/missingness.
It excludes algorithm names, nomination sources, ranks, model-generated
explanations, KNN/WSM scores, and rent assessments. No personal contacts or
authentication fields are exported. Target budget/priority facts are visible
as user requirements, not algorithm outcomes.

This is a preliminary framework, **not ready for human annotation**. Missing
journeys and model assessments, sparse inventory and area-proxy endpoints
prevent the intended independent full-method evaluation. A later pilot must
confirm readability, expert scenario validity, sufficient competition, ethics
requirements and annotation workload. Model-derived fairness assessments should
not anchor relevance judgments; any separately visible condition needs its own
prespecified sensitivity design.

At three raters/pair this pool implies 2,580 judgments. Assuming 1-3 minutes per
judgment gives 43-129 person-hours, excluding training/adjudication. This is an
assumption-based estimate, not a measured pilot. Pool-limited relevance is not
exhaustive-market ground truth; report unjudged rates and later nomination
coverage before interpreting NDCG/Recall/MAP.
