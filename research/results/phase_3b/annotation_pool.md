# Regenerated Annotation Pool

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

The old 860-pair pool stays untouched. New provisional pool: 4800
unique pairs. Per-profile counts: {'24': 200}.
Three independent annotators imply 14400
judgments. At an assumed 1-3 minutes each, total person-hours range:
[240.0, 720.0] (not a measured pilot).

Quota sampler reserves random eligible cases, up to three boundary exclusions,
near-budget eligible cases, interleaved property-type/area/rent/structural strata
and verified commute cases when available. Seed=42. There are no KNN/WSM results
or algorithm labels in the sampling input. Future baseline nominations can use
the existing pair-deduplicating union mechanism; pool-limited relevance is not
complete-market recall. Internal sampling sources remain separate from blinded
exports, which hide model assessments, names, ranks, scores and explanations.

Commute-incomplete pairs: 4800. These are not
final commute-judgment materials. No human or LLM relevance labels were made.
Suggested manageable allocation for later review: pilot on development profiles,
then balanced rater blocks (24 pairs x 3 judgments = 72 judgments per complete
profile, about 1.2-3.6 person-hours). Do not cut diversity or choose final profiles
after observing algorithm quality. Final assignment/pilot/ethics is future work.

Evidence: annotation_sampling_config.json, annotation_pool.json,
annotation_blinded_export.json and annotation_validation.json. Phase 4 cannot
begin on these missing-route exports.
