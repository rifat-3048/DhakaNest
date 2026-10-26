"""Render measured Phase 3B reports and seal them using existing manifest tools."""

import argparse
from pathlib import Path

from research.experiments.manifest import build_manifest, write_manifest_exclusive
from ..common import ROOT, RESEARCH, encode, read, write_once
from ..seal_phase3 import verify as verify_historical
from .fixture import DATA
from .inventory import sha

RESULTS = RESEARCH / "results/phase_3b"


def write_report(name, text):
    path = (RESULTS / name).resolve()
    if not path.is_relative_to(RESULTS.resolve()):
        raise ValueError("Unsafe report path.")
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(text.strip() + "\n")


def reports():
    verified = read(RESULTS / "verification_results.json")
    inventory = read(DATA / "inventory_coverage.json")
    coverage = read(DATA / "candidate_coverage.json")
    annotation = read(DATA / "annotation_validation.json")
    routing = read(DATA / "routing_matrix_validation.json")
    plan = read(DATA / "routing_acquisition_plan.json")
    assessment = read(DATA / "assessment_validation.json")
    geo = read(DATA / "geographic_coverage.json")
    audit = read(DATA / "inference_acquisition.json")
    shared = "Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed."
    docs = {
        "inventory_reconstruction.md": f"""# Inventory Reconstruction

{shared}

Reused original generate_inventory unchanged with seed 20261005, generator 1.0.0,
2500 active plus 100 lifecycle records. Generation of all 2600 preserves original
group allocation and random sequence before selecting the active subset.
Recovered {inventory['active']} approved/available synthetic records; retained
{inventory['lifecycle']} separate lifecycle audit records. IDs hash deterministic
academic seed keys. This is equivalent configured reconstruction, NOT a live DB
snapshot or confirmation of the current application's records. No MongoDB access.

Property types: {inventory['property_types']}. Furnishing: {inventory['furnishing']}.
Advertised rents BDT {inventory['rent_minimum']:,.0f}-{inventory['rent_maximum']:,.0f}.
Unique amenity combinations: {inventory['unique_amenity_combinations']}.
All records are academic_synthetic; none are real market observations. Contacts,
private addresses, administrator IDs and authentication details are excluded.
Full independent replay reproduced active/lifecycle records exactly. Genuine
routes remain missing; inventory alone does not enable final evaluation.

Evidence: properties.json, lifecycle_properties.json, generation_config.json,
inventory_coverage.json, dataset_manifest.json and verification_results.json.
""",
        "rent_assessment_provenance.md": f"""# Rent Assessment Provenance

{shared}

The existing saved XGBoost models, preprocessors and helper were genuinely used,
with all 12 declared artifact checksums plus the model manifest recorded and
verified. No training, test retuning or model file edits occurred. Inference uses
one thread in a dedicated research process. Original production assessment and
prediction functions remain unchanged.

Verified {assessment['verified']} generated assessments: 2500 active and 100
lifecycle; missing=0, fixture expected rents substituted=0. Routes:
{assessment['model_route_counts']}. The original two-stage generator made
{audit['actual_model_calls']} genuine prediction calls. Verification separately
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
""",
        "geographic_verification.md": f"""# Geographic Verification

{shared}

Represented broad areas: {geo['listing_areas']}.
The original generator's seeded +/-0.0015-degree offsets around 12 existing
repository anchors are preserved. All coordinates pass finite/Dhaka-bounds and
original offset checks; OSRM URLs use longitude,latitude. Unique property
coordinates: {geo['unique_property_coordinates']}; duplicate groups:
{geo['duplicate_coordinate_groups']}. Destination definitions: 12 area anchors,
unchanged coordinates from Phase 3A.

Independently verified precise property geocodes=0; independently verified
institution endpoints=0. Each property explicitly identifies synthetic offset
precision, area label, source, verification method and absent independent date.
Destination provenance similarly identifies area proxies. The old seed claims
OSM verification on 2026-08-26; it is repository evidence, not fresh verification.
No external geocoding or invented exact institution/property location was used.

This can support an area-anchor synthetic scenario study once genuine routes
exist, not claims about actual address-level commutes or Dhaka-wide geographic
generalization. Any future precise-location study needs separately enabled
research lookup and verifiable coordinate evidence.

Evidence: geographic_coverage.json, destinations.json, property provenance,
route_pair_manifest.jsonl. No source precision was promoted to verified geocodes.
""",
        "routing_completion.md": f"""# Routing Completion and Authorization Request

{shared}

Required unique full-grid route pairs: {routing['expected_pairs']}.
Genuine valid=0, supported unreachable=0, failed attempted=0, missing=
{routing['missing_pairs']}. No OSRM or geocoding endpoint was contacted. Missing
values remain null/status missing, not zero, unreachable, or straight-line routes.
Full-grid freezing supports future alternative candidate universes beyond KNN.

The route manifest binds stable pair IDs, listing/destination IDs, exact frozen
origin/target coordinates and driving profile. Route rows preserve source,
status, duration/distance, acquisition timestamp, engine/map version (unknown
until acquired), and explicit failure reason. Pair IDs eliminate duplicate pairs.

Production URL/parser and sealed capture machinery are reused: bounded serial
concurrency 1, 40 origins/20 destinations per request, one-second minimum pacing,
30-second timeout, two retries and immutable checkpoint/resume. Mocked tests
verify successes, failures, unreachable nulls, interrupted resume and raw-evidence
integrity; those artificial test values are never benchmark evidence.

Separate authorization needed: approve an OSRM endpoint for this research
capture, driving profile and 30,000 frozen pairs. Planned requests=
{plan['requests_without_retries']}, maximum with two retries=
{plan['maximum_requests_with_two_retries']}. Minimum pacing about one minute
plus service time; an all-timeout/retry path can approach 102 minutes. Approve
appropriate provider capacity and record engine/map versions where available.
The example http://127.0.0.1:5000 is not known to be running. Local operation
without Docker is supported; no server/deployment/package installation was run.

Use the opt-in command documented in benchmark/phase3b/README.md only after
explicit endpoint permission. Integrate genuine capture through attach_capture
into another new dataset version. Current benchmark must remain marked partial.

Evidence: routes.jsonl, route_pair_manifest.jsonl, routing_acquisition_plan.json,
routing_matrix_metadata.json, routing_matrix_validation.json, failure/log files.
""",
        "candidate_coverage.md": f"""# Candidate Coverage

{shared}

Original 200 profiles and 60-development/140-held-out partitions are preserved
byte-for-byte. No preferences were relaxed or optimized for desired outcomes.
All 2500 approved/available active properties enter base eligibility. Existing
production hard filters/commute checks are reused without KNN or WSM execution.

Hard-filter bins: {coverage['hard_filter']}.
Minimum/median/maximum survivors: {coverage['hard_count_min']} /
{coverage['hard_count_median']} / {coverage['hard_count_max']}.
Profiles with at least ten HARD survivors: {coverage['hard_filter']['ten_or_more']}.
First sequential exclusion totals: {coverage['first_exclusion_reasons']}.
These reasons do not count every simultaneous incompatibility. Exact sparse
profile IDs, families and all production stage counts are recorded in
candidate_coverage.json; no sparse queries are silently removed.

Commute bins remain {coverage['commute_feasible']}; profiles with ten
commute-feasible candidates remain unknown, not equal to the hard-filter count.
Unknown-commute profiles: {coverage['commute_unknown_profiles']}. Route-verified
profiles: {coverage['commute_verified_profiles']} (empty-hard-set cases require
no route calls). Candidate count before KNN cannot be finalized until routing.
No arbitrary substantial-subset acceptance threshold was invented after seeing
these counts; supervisor benchmark-design review remains necessary.

Evidence: candidate_universes.json, candidate_coverage.json, properties.json,
unchanged tenant_profiles.json/profile_splits.json. End-to-end methods start
from inventory; controlled pools are never the proposed KNN-selected subset.
""",
        "benchmark_feasibility.md": f"""# Benchmark Feasibility

{shared}

Structural diversity is present across all four types, canonical furnishings,
many amenity combinations and BDT {inventory['rent_minimum']:,.0f}-
{inventory['rent_maximum']:,.0f} model-linked synthetic rents. Twelve area-anchor
regions and 200 distinct scenario profiles are retained. Hard-filter coverage
supports ten-way competition for {coverage['hard_filter']['ten_or_more']} profiles
before commuting. Difficult/sparse cases stay in the dataset and are reported.

| Future comparison | Current support |
|---|---|
| Structural eligibility / candidate coverage | Supported offline; measured, not recommendation performance |
| KNN selection experiment | Structurally prepared; full pipeline partially supported until routing/labels |
| Five-criterion WSM v4 | Assessments and inputs prepared; ranking evaluation unsupported until routes/labels |
| Destination importance / max commute | Unsupported as an experiment without genuine frozen OSRM |
| Rent Fairness | Arithmetic/inference integrity supported; market validity limited by model-rent circularity |
| Area-first comparison | Structural/area inputs prepared; common routing/labels missing for full comparison |
| Single-destination control | Frozen request definitions prepared; experiments not executed, routing/labels missing |
| Journey-aware baseline | Protocol specified; not implemented, needs routes and independent labels |

Geographic coordinates are approximate synthetic offsets, not real property
observations; destinations are area proxies, not verified hospitals/workplaces.
Profile families are held out together but share inventory/geographic scope.
No real-market or IID generalization, causal component benefit, statistical
superiority, or actual commute variation has been demonstrated. Near-boundary
rent/size and random pool selection is a design feature, not human relevance.

Next evidence gate: separately authorized OSRM capture, new integrated version,
repeat commute competition, expert/pilot review of scenarios and workload,
then explicit Phase 4 authorization. No comparative outcomes were examined.
""",
        "annotation_pool.md": f"""# Regenerated Annotation Pool

{shared}

The old 860-pair pool stays untouched. New provisional pool: {annotation['pairs']}
unique pairs. Per-profile counts: {annotation['per_profile_distribution']}.
Three independent annotators imply {annotation['judgments_at_three_raters']}
judgments. At an assumed 1-3 minutes each, total person-hours range:
{annotation['person_hours_at_one_to_three_minutes_assumption']} (not a measured pilot).

Quota sampler reserves random eligible cases, up to three boundary exclusions,
near-budget eligible cases, interleaved property-type/area/rent/structural strata
and verified commute cases when available. Seed=42. There are no KNN/WSM results
or algorithm labels in the sampling input. Future baseline nominations can use
the existing pair-deduplicating union mechanism; pool-limited relevance is not
complete-market recall. Internal sampling sources remain separate from blinded
exports, which hide model assessments, names, ranks, scores and explanations.

Commute-incomplete pairs: {annotation['commute_incomplete_pairs']}. These are not
final commute-judgment materials. No human or LLM relevance labels were made.
Suggested manageable allocation for later review: pilot on development profiles,
then balanced rater blocks (24 pairs x 3 judgments = 72 judgments per complete
profile, about 1.2-3.6 person-hours). Do not cut diversity or choose final profiles
after observing algorithm quality. Final assignment/pilot/ethics is future work.

Evidence: annotation_sampling_config.json, annotation_pool.json,
annotation_blinded_export.json and annotation_validation.json. Phase 4 cannot
begin on these missing-route exports.
""",
        "offline_evaluation_readiness.md": f"""# Offline Evaluation Readiness

{shared}

BenchmarkFixture extends the sealed Phase 3A loader without edits. It validates
dataset/source hashes, byte-identical parent profiles/splits, actual-model
assessment provenance, synthetic coordinate precision and pair-coordinate
bindings. It loads all 2500 active properties, 200 profiles, 12 destinations,
30,000 route status rows and legitimate stored reconstruction assessments.
prepared_inputs(profile_id) returns deterministic candidate data and versions
(WSM v4, K=10, amended protocol 1.1.0-phase3), without ranked outcomes.

Works without MongoDB, a frontend, deployment, production credentials or live
OSRM. Missing routing causes require_experiment_ready to fail clearly, with no
fallback. The saved model is needed for provenance/replay, not runtime retraining.
The original budget formula clamp(1-rent/max_budget,0,1) is unchanged; travel
spending remains informational. Direct scalar regression tests confirm v4
behavior, not a second implementation or a ranking benchmark.

An opt-in capture wrapper records raw evidence, versions/statuses, logs and
route-pair metadata. attach_capture publishes another new integrated version,
rechecks raw responses and reconstructs candidates/pools. Genuine integration
was not executed because routing acquisition is not authorized. Prepared inputs
are functional; a fully experiment-ready matrix is still unavailable.
""",
        "phase_3b_verification.md": f"""# Phase 3B Verification

Status: **partially complete**. Offline inventory/model evidence recovered;
genuine OSRM evidence remains missing. No Phase 4 work or final evaluation.

Actually executed: {verified['research_tests']} research tests, zero skips,
all passed, including the original 75 and 22 new Phase 3B tests. Backend
regressions including academic inventory: {verified['backend_tests']} passed.
Python compilation passed. Full dataset validation, canonical candidate/pool
reconstruction, all 2600 prediction replays, full deterministic inventory rerun,
model/preprocessor manifest checks, coordinates, provenance and missing routing
checks passed. Mock route payloads are temporary test data only.

Historical checks: {verified['dataset_validation']['historical']}.
Production tracked diff empty. Phase 0-3A code/data/results/manifests unchanged;
all new files are under research/. Tenant request and split bytes unchanged.
No MongoDB access, database writes, production-source changes, installs, live
HTTP/geocoding, model training or deployment occurred. WSM/KNN/routes/formulas
remain production originals. No labels, metrics or superiority claims.

Outputs: 2500 active + 100 lifecycle synthetic properties, {assessment['verified']}
valid genuine-model assessments, 12 approximate area destinations, 30,000
missing road pairs, {annotation['pairs']} provisional blinded pool pairs.
Hard-filter bins: {coverage['hard_filter']}; commute bins unknown until routing.
All properties are reconstruction evidence, not real observed rentals or a
confirmation of live production inventory state. Synthetic rent/fairness
circularity and area-proxy limitations are documented in the companion reports.

Phase 3B manifest binds new code, tests, dataset and reports. Verification results
include actual test logs. Approve a routing endpoint and planned bounded request
volume before acquisition; then publish a new integrated dataset, rerun commute
feasibility and annotation review, and seek explicit Phase 4 authorization.
""",
    }
    for name, text in docs.items():
        write_report(name, text)


def seal():
    destination = RESULTS / "phase_3b_manifest.json"
    config_path = RESULTS / "phase_3b_config.json"
    if destination.exists() or config_path.exists():
        raise FileExistsError("Phase 3B seal exists; use --verify.")
    verified = read(RESULTS / "verification_results.json")
    outputs = [p.relative_to(RESEARCH).as_posix() for directory in (Path(__file__).parent, DATA, RESULTS)
               for p in directory.iterdir() if p.is_file() and p != destination]
    outputs += ["tests/test_phase3b.py", config_path.relative_to(RESEARCH).as_posix()]
    config = {"experiment_id": "phase_3b_inventory_and_offline_evidence", "purpose": "Reconstruct original academic inventory with genuine frozen inference; preserve missing OSRM and held-out profiles.",
              "dataset": {"identifier": "dhakanest-benchmark-v1.1", "path": "research/datasets/benchmark_v1_1/dataset_manifest.json"},
              "input_configuration": {"active_properties": 2500, "lifecycle_properties": 100, "profiles": 200,
                                      "missing_routes": 30000, "database_access": "none", "external_requests": 0,
                                      "research_tests": verified["research_tests"], "backend_tests": verified["backend_tests"]},
              "random_seed": 20261005, "versions": {"scoring": "wsm_v4", "protocol": "1.1.0-phase3", "dataset": "1.1.0"},
              "dependencies": ["python", "xgboost", "scikit-learn", "joblib", "numpy", "pandas", "scipy"],
              "output_paths": sorted(set(outputs)), "database_access": "none", "execution_status": "partially_complete_missing_genuine_OSRM"}
    write_once(config_path, config)
    manifest = build_manifest(config, repo_root=ROOT, research_root=RESEARCH)
    write_manifest_exclusive(manifest, destination, research_root=RESEARCH)
    return verify()


def verify():
    manifest = read(RESULTS / "phase_3b_manifest.json")
    for row in manifest["outputs"]:
        path = (RESEARCH / row["path"]).resolve()
        if not path.is_relative_to(RESEARCH.resolve()) or sha(path) != row["sha256"]:
            raise ValueError(f"Phase 3B output changed: {row['path']}")
    if sha(ROOT / manifest["dataset"]["path"]) != manifest["dataset"]["sha256"]:
        raise ValueError("Dataset manifest changed.")
    return {"phase_3b_output_hashes_verified": len(manifest["outputs"]), "historical": verify_historical()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(encode(verify()))
    else:
        reports()
        print(encode(seal()))


if __name__ == "__main__":
    main()
