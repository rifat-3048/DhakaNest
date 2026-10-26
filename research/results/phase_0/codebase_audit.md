# Phase 0 Codebase Audit

Audit basis: repository commit `45e4d040699c86ed535fa0c8582d77829503697d`.
No production module was imported or executed as part of this audit.

## Production recommendation path

| Component | Existing path and entry points | Inputs and outputs | External dependency and safe reuse |
|---|---|---|---|
| API entry | `backend/app/routes/recommendations.py`: `get_recommendation_candidates`, `get_commute_recommendation_candidates`, `get_commute_scored_recommendation_candidates`, `get_knn_candidates`, `get_ranked_recommendation_results` | Authenticated tenant request to staged/final response; ranked route can persist history | **Adapter required.** Route dependencies load auth/database and final route can call history persistence. Do not use in offline experiments. |
| Eligibility and hard filters | `backend/app/services/recommendation_service.py`: `calculate_effective_maximum_rent`, `filter_recommendation_candidates`, `get_filtered_recommendation_candidates` | Tenant preferences plus listing documents to eligible candidates and filter diagnostics | Pure filter is reusable. Database wrapper reads MongoDB and requires a read-only fixture adapter. Base query requires approved and available listings. |
| Routing | `backend/app/services/routing_service.py`: `build_osrm_table_url`, `parse_osrm_table_response`, `OSRMRoutingProvider`, `build_routing_adapter`; `routing_infrastructure.py`: `ManagedRoutingProvider`, caches and circuit breaker | Coordinates to duration/distance matrices and route geometry | URL builders/parsers are offline-safe. Providers make HTTP calls to OSRM. Future experiments must inject frozen matrices or a deterministic provider. |
| Location suitability | `recommendation_service.py`: `apply_commute_routes`, `score_destination_access`, `get_destination_access_scored_candidates` | Candidate routes and weighted destinations to `[0,1]` destination-access scores; max-commute violations are removed | Scoring functions are reusable with schema objects and frozen routing output. Service orchestration needs an adapter. |
| Content-based KNN | `backend/app/services/property_knn_service.py`: `calculate_tenant_area_target`, `build_property_feature_space`, `select_property_neighbors` | Hard-filter survivors and tenant preferences to normalized feature matrices, cosine similarity, and top neighbors | Reusable offline with NumPy/scikit-learn and schema objects. `k` is supplied by the caller; production uses configured K. No network/database calls in this module. |
| WSM v4 | `backend/app/services/wsm_service.py`: `calculate_budget_score`, criterion scorers, `normalize_priority_weights`, `calculate_weighted_suitability`, `rank_knn_candidates` | KNN survivors and 1-5 priorities to five normalized criteria, normalized weights, final rank, and explanations | Criterion functions are deterministic. Module import loads `app.config.settings`; use a thin research adapter or controlled environment. It does not call MongoDB/OSRM. |
| Rent fairness | `backend/app/services/rent_fairness_service.py`: `classify_rent_fairness`, `build_input_snapshot`, `assessment_matches_listing`, `build_rent_assessment` | Listing facts and local XGBoost prediction to stored assessment; WSM reads `difference_percent` | Snapshot/classification logic is reusable. Prediction requires local model bundle. Recommendation ranking deliberately does not invoke prediction. |
| Explanations | `backend/app/services/recommendation_explanation_service.py`: `build_recommendation_reasons` and criterion-specific helpers | Ranked candidate and preferences to deterministic reason records | Reusable offline with schema objects; no live service calls. |
| History | `backend/app/services/recommendation_history_service.py`: snapshot serializers, `save_recommendation_run`, list/detail methods | Ranked response to MongoDB snapshots and history API models | Serializers need separation/adaptation. Index/save/list/detail functions access MongoDB and are forbidden in research experiments. |
| Contact enrichment | `recommendation_service.py`: `attach_landlord_contacts` | Ranked listing owner references to contact objects | Reads MongoDB users; exclude from relevance experiments or provide an inert adapter because it does not affect ranking. |

## Evaluation and evidence utilities

| Component | Existing path | Audit finding |
|---|---|---|
| Metric formulas | `backend/app/evaluation/recommendation_metrics.py`: `precision_at_k`, `dcg_at_k`, `ndcg_at_k` | **Verified reusable.** NDCG uses exponential gain `(2^relevance - 1)` and log2 discount. Pure and offline. |
| Evaluator | `backend/app/evaluation/recommendation_evaluator.py`: `load_ground_truth`, `validate_ground_truth`, `load_seed_inventory`, `evaluate_recommendations` | Evaluates the unchanged final pipeline through an in-memory read-only listing collection. Safe only when complete seed documents and a deterministic routing provider are supplied. |
| Evaluation CLI | `backend/scripts/evaluate_recommendations.py` | **Not offline-reproducible as-is.** Reads seed documents from MongoDB and defaults to the production OSRM adapter. It performs no writes, but external state can change results. |
| Benchmark labels | `backend/evaluation/recommendation_ground_truth.json` | 8 profiles, 12 identifiers, 96 complete 0-3 judgments. It does not contain complete listings or route matrices. |
| Recommendation tests | `backend/tests/test_recommendation_part1.py` through `test_recommendation_part10.py` | Include deterministic fake routing, criterion regressions, evaluator validation, history behavior, and API/serialization checks. Useful regression basis, not a frozen benchmark run. |
| Academic inventory | `backend/app/services/academic_inventory_service.py`; seed scripts under `backend/scripts/` | `generate_inventory`, fingerprints, coverage, and probe functions can run offline. `apply_generated_inventory` and cleanup/seed scripts write MongoDB and are excluded. |
| ML notebooks | `ml/notebooks/00_...` through `04_...` | Data preparation, Random Forest, XGBoost, CatBoost, comparison/export. Reuse only against checksummed copies and record environments/seeds. |
| ML evidence | `ml/evidence/{manifests,metrics,reports,figures}`; `ml/exports/` | 53 local evidence files, including 17 figures, candidate predictions, official test outputs, manifests, and reports. Existing official test artifacts are immutable inputs. |

## Architecture conclusions

- **Verified:** production order is approved/available eligibility, hard filters,
  OSRM commute processing, destination scoring, KNN selection, then five-factor
  WSM ranking. KNN similarity is not a sixth WSM criterion.
- **Verified:** the cleanest offline seam is below the API layer: explicit
  listing fixtures plus an injected routing provider passed to the existing
  evaluator/service functions.
- **Unresolved:** a fully frozen recommendation fixture does not exist. Current
  benchmark reproduction depends on local MongoDB listing state and OSRM.
- **Required adapter:** future research should deserialize frozen listing and
  route fixtures into existing schemas, set explicit settings, and call the
  production pipeline read-only. It must never use route handlers or history
  persistence.
