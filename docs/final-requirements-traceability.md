# Final Requirements Traceability

Status values describe the checked-in implementation: `PASS`, `PARTIAL`,
`NOT IMPLEMENTED`, or `NOT APPLICABLE`.

| ID | Requirement | Implemented component | API/UI evidence | Automated test evidence | Status |
| --- | --- | --- | --- | --- | --- |
| REQ-AUTH-01 | Tenant and landlord can register; public admin registration is blocked | `auth_service.py`, user schemas | `POST /auth/register`, register form | Manual API acceptance; role validation covered through guards | PASS |
| REQ-AUTH-02 | All roles can log in with JWT | auth route/service/security | `POST /auth/login`, login form | Protected-route tests across Parts 1 and 8 | PASS |
| REQ-AUTH-03 | Current user can be resolved | auth dependency | `GET /auth/me` | `test_missing_authentication_is_rejected` | PASS |
| REQ-AUTH-04 | Role boundaries protect tenant, landlord, and admin operations | dependencies and route guards | protected dashboards and APIs | `test_role_dependency_allows_tenant_and_rejects_other_roles`, `test_non_landlord_roles_are_denied` | PASS |
| REQ-TEN-01 | Tenant supplies housing needs without selecting a residential area | recommendation schema and preference form | tenant dashboard form | `tenant-data-readiness.test.ts` | PASS |
| REQ-TEN-02 | Tenant supplies 1-3 resolved destinations with importance 1-5 | destination schema/editor | destination editor | `tenant-destination.test.ts` | PASS |
| REQ-TEN-03 | Optional maximum commute is supported per destination | recommendation schema/service | preference form and commute results | `test_maximum_and_overall_location_priority_do_not_change_score` plus Part 2 suite | PASS |
| REQ-TEN-04 | Five ranking priorities are accepted | priority schema/UI | priority selector | `test_priority_values_must_be_between_one_and_five` | PASS |
| REQ-TEN-05 | Household size is descriptive only | schema/storage only | preference summary | Part 4 exclusion tests and `tenant-data-readiness.test.ts` | PASS |
| REQ-TEN-06 | Ranked results, details, errors, and placeholders are distinct | tenant result components | recommendations pages | `recommendation-results.test.ts` | PASS |
| REQ-LAND-01 | Landlord creates and edits owned draft/revised listings | listing service/routes | landlord listing form/detail | listing readiness and lifecycle suites | PASS |
| REQ-LAND-02 | Canonical property, furnishing, and amenity values are used | listing schemas and shared frontend options | listing form | `test_canonical_property_furnishing_and_amenity_values_are_enforced` | PASS |
| REQ-LAND-03 | Listing images are validated and managed through Cloudinary | image service/listing routes | image manager | listing lifecycle/readiness tests | PASS |
| REQ-LAND-04 | Complete listing can be submitted for review | listing service | `POST /api/listings/{listing_id}/submit` | listing lifecycle suite | PASS |
| REQ-LAND-05 | Landlord cannot modify another landlord's listing | ownership query/guard | protected listing APIs | `test_other_landlord_cannot_change_listing` | PASS |
| REQ-LAND-06 | Approved owned listing can be marked rented | listing lifecycle service | mark-rented action/API | listing lifecycle suite | PASS |
| REQ-ADM-01 | Admin lists and opens review records | admin listing routes/UI | admin dashboard/detail | listing lifecycle tests and OpenAPI validation | PASS |
| REQ-ADM-02 | Admin runs rent fairness before approval | fairness service/admin route | fairness panel | listing lifecycle and eligibility suites | PASS |
| REQ-ADM-03 | Admin approves, rejects, or requests revision with rules | admin decision route/service | decision panel | listing lifecycle suite | PASS |
| REQ-RENT-01 | Exported XGBoost bundle uses five production features and `log1p` target | model bundle/predictor | fairness endpoint | model artifact reload evidence and backend tests | PASS |
| REQ-RENT-02 | Fairness is based on stored prediction with +/-15% band | fairness service | admin assessment | rent/listing tests | PASS |
| REQ-RENT-03 | Assessment snapshot/version metadata is stored | fairness and listing services | admin review detail | listing eligibility tests | PASS |
| REQ-RENT-04 | Recommendations read assessment and never rerun prediction | recommendation/WSM services | criterion breakdown | Part 5 tests | PASS |
| REQ-REC-01 | Only approved, available, coordinate-valid listings are eligible | listing eligibility service | ranked API | listing recommendation eligibility tests | PASS |
| REQ-REC-02 | Budget, type, rooms, area, furnishing, move-in, and must-have amenities are hard filters | recommendation service | ranked API filter summary | Part 1 suite | PASS |
| REQ-REC-03 | Nice-to-have amenities are not hard filters | recommendation service | preference/results flow | `test_must_have_is_subset_nice_to_have_is_not_a_filter` | PASS |
| REQ-REC-04 | OSRM provider abstraction supplies listing-to-destination road metrics | routing service/infrastructure | ranked API commute details | Part 2 and Part 10 suites | PASS |
| REQ-REC-05 | Routing outage is distinct from zero matches; no straight-line fallback | routing/recommendation routes | separate error state | Part 2 and frontend API/results tests | PASS |
| REQ-REC-06 | Destination scores are min-max normalized and importance weighted | recommendation service | location criterion | Part 3 suite | PASS |
| REQ-REC-07 | Deterministic content-based KNN uses scaling, block normalization, cosine, and effective K | property KNN service | similarity diagnostic | Part 4 suite | PASS |
| REQ-REC-08 | WSM uses exactly location, budget, space, amenities, and rent fairness | WSM service | criterion breakdown | Part 5 suite | PASS |
| REQ-REC-09 | Priorities normalize by their sum and ranking has deterministic ties | WSM service | authoritative backend rank | `test_weights_are_raw_priority_over_sum` and Part 5 suite | PASS |
| REQ-REC-10 | Explanations are deterministic and do not change score/rank | explanation service | recommendation cards/details | Part 6 suite | PASS |
| REQ-EVAL-01 | Benchmark has 8 profiles, 12 listings each, and 96 judgments | ground-truth JSON/evaluator | evaluation command | Part 7 dataset tests | PASS |
| REQ-EVAL-02 | Precision@K uses relevance >=2 and short-list denominator | metric module | evaluator output | Part 7 metric tests | PASS |
| REQ-EVAL-03 | NDCG@K uses graded relevance and ideal ordering | metric module | evaluator output | Part 7 metric tests | PASS |
| REQ-HIST-01 | Successful explicit search persists once per tenant/idempotency key | history service/routes | history pages | `test_same_tenant_and_key_reuses_one_run` | PASS |
| REQ-HIST-02 | History is newest-first and tenant-isolated | history service | history list/detail | `test_history_is_tenant_isolated_newest_first_and_summarized` | PASS |
| REQ-HIST-03 | Stored snapshot is immutable and retrieval reruns no ranking services | history service | historical detail | Part 8 suite and frontend history tests | PASS |
| REQ-MAP-01 | Current and historical results show ranked homes and destinations | map components | results/history maps | `recommendation-map.test.ts` | PASS |
| REQ-MAP-02 | Card/marker selection and rank-one default stay synchronized | map explorer | interactive map | `recommendation-map.test.ts` | PASS |
| REQ-MAP-03 | Selected-home route geometry is cached and failure is partial | geometry route/infrastructure | selected map routes | Parts 9-10 and frontend map tests | PASS |
| REQ-MAP-04 | Geometry never replaces stored commute metrics or rank | history/route service and map utilities | map panel | `geometry response has no power to replace commute metrics` | PASS |
| REQ-OPS-01 | Local liveness/readiness expose safe status | health routes | `/health`, `/ready`, `/health/routing` | Part 10/11 tests | PASS |
| REQ-OPS-02 | Cache, single-flight, retry, circuit breaker, and fallback are bounded | routing infrastructure | routing health | Part 10 suite | PASS |
| REQ-OPS-03 | Tenant-scoped rate limits protect recommendation and geometry APIs | rate-limit core/routes | HTTP 429 behavior | Part 10 and frontend API tests | PASS |
| REQ-OPS-04 | Request IDs, structured logs, and security headers are present | main/observability | API response headers | Part 10/11 tests | PASS |
| REQ-OPS-05 | Required MongoDB indexes are validated | index validation/startup | pre-flight/index script | Part 11 tests | PASS |

## Status Summary

Total requirements: **48**. PASS: **48**. PARTIAL: **0**. NOT IMPLEMENTED:
**0**. NOT APPLICABLE: **0**. Screenshot capture, report insertion, and slide
editing are submission tasks rather than application requirements.
