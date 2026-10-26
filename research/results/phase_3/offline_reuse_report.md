# Offline Production-Code Reuse

Implemented preparation works in a dedicated research Python process using the
existing backend virtual environment. No new packages were installed. The
adapter imports settings in an empty temporary working directory with a cleared,
inert environment, avoiding private .env and API credentials. It refuses to reuse
an already production-configured process. These process-local imports/settings
do not change source files or a separately running application.

| Production component | Phase 3 use |
|---|---|
| TenantRecommendationRequest | Validate all 200 requests |
| RecommendationCandidate | Validate property-to-pipeline contracts |
| is_recommendation_eligible | Apply approved/available/valid-coordinate gate |
| filter_recommendation_candidates | Exact hard filters and exclusion diagnostics |
| apply_commute_routes | Candidate preparation with explicit frozen matrix adapter |
| build_osrm_table_url / parse_osrm_table_response | Opt-in capture and raw evidence verification; no live calls |
| KNN / WSM | Import dependencies only; ranking not invoked |
| rent assessment / model | Consume stored assessment contract only; no inference |
| database / routes / history / contact lookup | Not invoked |

The recommendation module transitively imports listing/rent-model modules.
The existing bundle's inference helper imports its libraries; no predictor
instance/model load or prediction is requested. This offline reuse still needs
the repository/backend Python dependencies and existing helper code, not a
running database, frontend, routing service, or production credentials.

`OfflineFixture` loads frozen properties, profiles, destination definitions,
route data, configuration metadata, and assessments when present. It verifies
source/dataset hashes, schema contracts, coordinate provenance and route
evidence. `prepare(profile_id)` returns diagnostic candidates without ranking.
`FrozenRoutingProvider` implements the production matrix interface and fails
on missing routes or coordinate drift. It never invokes a live fallback.

`require_experiment_ready()` currently fails on 144 absent road pairs and missing
stored assessments. Data loading/candidate preparation are functional; complete
ranked benchmarking is **not executable** on this v1 fixture. Baselines, scoring
runners, ranking metrics and statistical comparisons remain later-phase work.
The offline validators are not substitutes for independent source verification,
human scenario review, or real-world external validation.
