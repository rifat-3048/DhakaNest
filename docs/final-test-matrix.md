# Final Test Matrix

| Test area | Type | Important scenarios | Result | Evidence |
| --- | --- | --- | --- | --- |
| Authentication | unit/integration | missing auth, tenant guard, role rejection | PASS | Parts 1 and 8 backend tests |
| Listing lifecycle | unit/integration | ownership, approve-to-rented, invalid transitions | PASS | `test_listing_lifecycle.py` |
| Listing readiness | schema/service | canonical values, coordinates, submission data | PASS | `test_listing_data_readiness.py`, `test_listing_recommendation_eligibility.py` |
| Rent model | artifact/service | load, five features, transform, stored fairness | PASS | exported manifests and backend regression suite |
| Recommendation Part 1 | unit/integration | eligibility and all hard filters | PASS | `test_recommendation_part1.py` |
| Part 2 | unit/integration | OSRM matrix, direction, commute constraint, outage | PASS | `test_recommendation_part2.py` |
| Part 3 | unit | normalization, equal duration, importance | PASS | `test_recommendation_part3.py` |
| Part 4 | unit/integration | feature order, scaling, cosine, effective K | PASS | `test_recommendation_part4.py` |
| Part 5 | unit/integration | five WSM criteria, weights, ties, sensitivity | PASS | `test_recommendation_part5.py` |
| Part 6 | unit/frontend | deterministic reasons and unchanged rank | PASS | `test_recommendation_part6.py`, results tests |
| Part 7 | metric/evaluation | ground truth, Precision@K, NDCG@K | PASS | `test_recommendation_part7.py`, evaluation evidence |
| Part 8 | integration/frontend | persistence, idempotency, isolation, snapshots | PASS | `test_recommendation_part8.py`, history tests |
| Part 9 | integration/frontend | markers, synchronization, routes, history map | PASS | `test_recommendation_part9.py`, map tests |
| Part 10 | unit/integration | cache, retry, breaker, fallback, limits, probes | PASS | `test_recommendation_part10.py` |
| Local operations | validation | config, indexes, model, OpenAPI, headers | PASS | `test_production_part11.py`, pre-flight scripts |
| Frontend | unit/static/build | API errors, form data, result/history/map display | PASS | Node test suite, TypeScript, ESLint, normal build |
| Security/error handling | unit/integration | 401/403/409/422/429/503 and safe errors | PASS | backend and frontend suites |

The full manual role demonstration remains on the examiner checklist because it
uses local demo accounts and visible browser interaction.
