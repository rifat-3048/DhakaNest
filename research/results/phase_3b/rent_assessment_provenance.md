# Rent Assessment Provenance

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

The existing saved XGBoost models, preprocessors and helper were genuinely used,
with all 12 declared artifact checksums plus the model manifest recorded and
verified. No training, test retuning or model file edits occurred. Inference uses
one thread in a dedicated research process. Original production assessment and
prediction functions remain unchanged.

Verified 2600 generated assessments: 2500 active and 100
lifecycle; missing=0, fixture expected rents substituted=0. Routes:
{'primary': 2600}. The original two-stage generator made
5200 genuine prediction calls. Verification separately
replayed every saved prediction and rebuilt the entire inventory identically.
Input snapshots, output hashes, model-route values, percentage arithmetic,
15% bands and production classifications all match.

These are freshly computed reconstruction assessments, not historical admin
approvals. Nonsemantic checked_at/checked_by fields are excluded; actual fresh
run timestamps are in inference_acquisition.json, not fabricated review dates.

Critical limitation: asking rents were themselves generated from these model
predictions times 0.68/0.82/1.00/1.20/1.35 and rounded to BDT 500. Fairness
values are internally legitimate but circular as market-quality evidence.
Fairness ranking utility requires independent human judgments/real-data analyses,
not agreement with these manufactured rent multipliers. The production fairness
formula and five WSM criteria were not changed.

Evidence: assessment_validation.json, inference_acquisition.json,
generation_config.json, each record's assessment_provenance and input_snapshot.
