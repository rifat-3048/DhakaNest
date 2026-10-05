# DhakaNest Backend

This folder contains the FastAPI backend for DhakaNest.

Local environment, health, index, backup, smoke, load-test, and rollback
guidance is documented in `../docs/local-setup.md`,
`../docs/operations.md`, and `../docs/local-submission-checklist.md`.

## What Exists Now

- A FastAPI app with health and database health endpoints.
- Environment-based configuration using `pydantic-settings`.
- MongoDB connection setup using Motor.
- Authentication for tenant, landlord, and admin users.
- Public registration for tenant and landlord users only.
- JWT login, current-user lookup, and role-based support.
- A complete landlord listing and admin review lifecycle.
- Base recommendation eligibility and tenant hard-filter candidate retrieval.
- OSRM road routing, max-commute filtering, and destination-access scoring.

## What Will Be Added Later

- Recommendation scoring and ranking.
- Recommendation result persistence.

## Run Locally

From the `backend` directory, activate the virtual environment and start FastAPI:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

## Create the First Admin

Public `/auth/register` requests cannot create admin accounts. Use the
controlled terminal script instead.

Before running it, make sure:

- `backend/.env` contains the correct `MONGO_URI` and `DATABASE_NAME`.
- MongoDB Server is running.
- The backend virtual environment is activated.

From the `backend` directory, run:

```powershell
python scripts/create_admin.py
```

Enter the admin name, email, Bangladeshi phone number, and password when
prompted. The password is hidden while typing and must be entered twice. The
script validates the details, checks that the email is unused, hashes the
password with the backend's existing password hasher, and then creates the
admin.

Never create an admin in MongoDB Compass using a plaintext password. The login
system expects a secure value in `password_hash`; storing the original password
would be insecure and would not produce a valid login.

## Audit Listing Coordinates

The recommendation inventory requires approved, available listings with valid
latitude and longitude. To inspect existing listings without changing any data,
run this command from the `backend` directory:

```powershell
python scripts/audit_listing_coordinates.py
```

The script reports readiness counts and identifies coordinate-incomplete records.
It never guesses coordinates, changes listing statuses, or writes to MongoDB.

## Seed Recommendation Development Listings

To create the idempotent development inventory, run this command from the
`backend` directory:

```powershell
python scripts/seed_recommendation_listings.py
```

The script uses the first active landlord and admin accounts in deterministic
email order, validates 12 varied listings through the backend schema, and stores
real assessments from the existing rent model. A sparse development key prevents
duplicates when the command is run again. Seed listings intentionally omit
Cloudinary images because images are not part of backend recommendation eligibility.

## Check Recommendation Candidates

To run the read-only Recommendation Part 1 scenarios against the local database:

```powershell
python scripts/check_recommendation_candidates.py
```

The script reports base eligibility, every hard-filter diagnostic count, and
the matching titles for five development requests. It does not rank results,
persist recommendation runs, or modify listing data.

## Recommendation Commute Routing

`POST /api/recommendations/commute-candidates` extends the Part 1 hard-filter
pipeline with road distance and estimated driving duration for every surviving
listing and important destination. Supplied maximum commute times are enforced
as hard constraints after routing.

Development routing uses the OSRM Table API with these safe environment values:

```env
ROUTING_PROVIDER=osrm
ROUTING_BASE_URL=https://router.project-osrm.org
ROUTING_TIMEOUT_SECONDS=10
ROUTING_USER_AGENT=DhakaNest-University-Development/0.1
```

The public OSRM server requires no API key and is a best-effort development
service, not production infrastructure. Its driving-profile durations are road
estimates only: they do not include live traffic, Dhaka congestion, public
transport, or walking conditions. A future hosted system should configure a
self-hosted or contracted routing provider with an appropriate service level.

To run the read-only commute scenarios against local listings:

```powershell
python scripts/check_recommendation_commutes.py
```

The script uses Nominatim-verified Dhaka destination coordinates, calls routing,
prints aggregate and per-candidate measurements, and never changes MongoDB data.

## Destination-Access Scoring

`POST /api/recommendations/commute-scored-candidates` extends commute-ready
candidates with one location criterion named `destination_access_score`.
For each destination, precise route durations are normalized independently:

```text
1 - ((duration - min_duration) / (max_duration - min_duration))
```

The fastest candidate receives `1.0`, the slowest receives `0.0`, and candidates
between them receive proportional values. If all durations are equal, every
candidate receives `1.0` for that destination. A single surviving candidate also
receives `1.0` because there is no weaker candidate in the comparison set.

Destination scores are combined with the tenant's destination importance values:

```text
sum(destination_score * importance) / sum(importance)
```

The resulting score is between `0.0` and `1.0`. It is relative to the candidates
surviving Part 2, so adding or removing candidates can change the scores. It is
not a probability, confidence percentage, final recommendation score, or rank.
The tenant's overall `priorities.location` value is reserved for the later
Weighted Sum Model and is not applied during destination-access scoring.

Run the read-only Part 3 development scenarios with:

```powershell
python scripts/check_recommendation_commute_scores.py
```

The script reports single-destination normalization, two-destination importance
weighting, and an importance-sensitivity check that reuses the same routes.

## Content-Based Property KNN

`POST /api/recommendations/knn-candidates` extends Parts 1-3 with nearest-property
selection. This is instance-based content recommendation, so it does not train a
new predictive model: the current Part 3 candidates are the neighbor dataset and
the tenant preference vector is the query.

The deterministic 20-dimensional feature space contains property type (4),
furnishing (3), scaled bedrooms/bathrooms/area (3), and canonical nice-to-have
amenities (10). Numeric values are min-max scaled using only the current candidate
pool plus the tenant target. Each semantic block is L2-normalized before the
blocks are concatenated so a larger block does not dominate merely because it
has more columns.

`preferred_area_sqft` supplies the tenant's structural area target. It is a soft
preference, not a minimum or maximum constraint: properties closer to it receive
stronger KNN similarity, while more distant sizes remain eligible but receive
weaker similarity. When it is absent, KNN retains its candidate-median fallback.
Legacy callers may still submit explicit minimum/maximum area bounds, which keep
their original hard-filter behavior.

Budget, asking rent, commute measurements, `destination_access_score`, rent
fairness, household size, move-in date, and overall tenant priorities are
intentionally excluded from the KNN vector. They are hard-filter inputs or
separate criteria for the later Weighted Sum Model, so including them here would
double-count unrelated signals.

The implementation uses scikit-learn's brute-force `NearestNeighbors` with cosine
distance:

```text
property_similarity_score = 1 - cosine_distance
```

`property_similarity_score` is a content-similarity measure between `0.0` and
`1.0`; it is not probability, accuracy, or confidence. KNN selection is also not
the final DhakaNest recommendation ranking. The selected neighbors continue to
the later Weighted Sum Model.

The development default is configurable in `backend/.env`:

```env
RECOMMENDATION_KNN_K=10
```

Ten is a configurable product/development choice, not a universally optimal
value. It can be evaluated later with ranking metrics such as Precision@K and
NDCG@K. The effective value is always the smaller of configured K and the Part 3
candidate count.

Run the read-only Part 4 broad, specific, amenity-sensitivity, and K-sensitivity
checks with:

```powershell
python scripts/check_recommendation_knn.py
```

The amenity and K checks reuse already routed candidates and the script never
changes MongoDB records.

## Weighted Sum Recommendation Ranking

`POST /api/recommendations/ranked` runs the full Parts 1-5 pipeline and creates
the current final DhakaNest ranking. It combines exactly five independent
criteria:

```text
location      = destination_access_score from Part 3
budget        = estimated-spend (or legacy rent-only) affordability score
space         = mean of bedroom, bathroom, and area compatibility
amenities     = nice-to-have amenity match count / preferred count
rent fairness = max(0, 1 - abs(stored difference_percent) / 30)
```

For a new request where every destination has `travel_days_per_month`, the
budget amount is estimated monthly spend rather than rent alone:

```text
monthly travel cost = sum(
  one-way OSRM road distance
  * 2
  * travel days per month
  * configured BDT per km
)
estimated monthly spend = advertised rent + monthly travel cost
```

`TRANSPORT_COST_PER_KM_BDT` controls the fixed rate. The local development
configuration uses `15` BDT/km as an explicit academic assumption, not a claim
about an exact real-world fare. One travel day means one round trip. The model
does not distinguish transport modes, multiple daily trips, traffic pricing, or
fuel-price changes. Duration still controls location convenience; distance is
reused for this advisory cost estimate. Destination importance never multiplies
travel cost.

If any destination lacks frequency, the request remains backward compatible:
no partial travel total is claimed and budget scoring remains rent-only. The
early hard budget filter always uses advertised rent because routing happens
later. Rent fairness still evaluates advertised rent independently.

For new preferred-area requests, area compatibility uses symmetric continuous
decay with a 40% tolerance:

```text
relative difference = abs(listing area - preferred area) / preferred area
area fit = max(0, 1 - relative difference / 0.40)
```

Preferred floor size is therefore a soft target, not a minimum or maximum
constraint. Substantially different sizes receive weaker space-fit scores but
are not excluded by this preference alone. Area remains inside the existing
space criterion alongside bedrooms and bathrooms; it is not a sixth criterion.

Approved listings must already have a current admin-review rent assessment.
Part 5 reads `rent_assessment.difference_percent`; it does not run XGBoost or
rebuild the assessment. Missing or unusable assessment data is treated as an
inconsistent approved listing rather than silently inventing a fairness score.

Tenant priorities are relative weights from 1 to 5. Each weight is normalized:

```text
normalized weight = priority / sum(all five priorities)
```

The Weighted Sum Model then calculates:

```text
final suitability = sum(criterion score * normalized priority weight)
```

Calculations use unrounded values; public criterion scores, weights, and final
scores are rounded consistently. `property_similarity_score` remains visible as
KNN candidate-selection diagnostics, but it is not included in the WSM formula.
This prevents property and amenity information from being counted twice.

`final_suitability_score` is a normalized `0.0-1.0` suitability score. It is not
a probability, confidence percentage, predictive accuracy, or guarantee of
tenant satisfaction. Candidates are ranked by final suitability descending,
then property similarity descending for ties, then their stable Part 4 order.

Run the read-only balanced, commute, budget, amenity, fairness, and KNN-separation
checks with:

```powershell
python scripts/check_recommendation_wsm.py
```

The script routes once, reuses the same Part 4 candidate set, reads stored
assessments, and never changes MongoDB records.

Run the read-only 1,200 sq ft preferred-area comparison with:

```powershell
python scripts/check_preferred_area.py
```

Run the read-only two-destination monthly travel-cost check with:

```powershell
python scripts/check_travel_cost.py
```

## Transparent Recommendation Reasons

Final ranked candidates include three-to-five concise reasons generated by
deterministic rules in the backend. The explanation layer reads structured
criterion scores, tenant priorities, listing facts, commute estimates, and the
stored rent assessment. It does not use an LLM, call a generative AI API, rerun
rent prediction, alter the WSM score, or change ranking.

Reason categories are limited to location, budget, space, amenities, rent
fairness, and property match. The strongest concrete facts are ordered using
tenant priorities and centralized score thresholds. Commute wording always says
"estimated drive" because OSRM durations are traffic-free road estimates, not
live Dhaka traffic times.

The final tenant endpoint remains:

```text
POST /api/recommendations/ranked
```

Run the complete read-only ranked explanation check with:

```powershell
python scripts/check_recommendation_explanations.py
```

## Recommendation Evaluation

Recommendation Part 7 evaluates the unchanged final ranked pipeline against a
controlled development benchmark in
`evaluation/recommendation_ground_truth.json`. The benchmark contains eight
realistic tenant profiles and an independent judgment for every one of the 12
seeded recommendation listings. Stable `development_seed_key` values are used
instead of MongoDB IDs or listing titles.

Ground truth must be assigned from explicit tenant requirements and listing
facts before reviewing algorithm output. Labels must never be derived from final
rank, final suitability, property similarity, or destination-access scores. The
graded scale is:

```text
3 = Highly Relevant
2 = Relevant
1 = Slightly Relevant
0 = Not Relevant
```

Precision treats relevance `2` and `3` as binary relevant. Precision@K uses
`min(K, recommendations returned)` as its denominator and returns `0.0` when no
recommendations are returned. It answers: how many of the top-K homes are judged
genuinely relevant?

NDCG uses graded gain `2^relevance - 1`, logarithmic rank discount, and an ideal
ordering built from all 12 judgments for the profile. It returns `0.0` when the
ideal DCG is zero. NDCG answers: does the system place the most relevant homes
near the top? Neither metric is model accuracy, confidence, or probability.

Run the complete read-only evaluation from the backend directory:

```powershell
python scripts/evaluate_recommendations.py
```

The command validates the benchmark and current seed inventory, runs every
profile through the same `get_ranked_recommendations` orchestration used by
`POST /api/recommendations/ranked`, and prints per-profile Precision@5,
Precision@10, NDCG@5, NDCG@10, ranking audits, and equal-weight macro averages.
It reads MongoDB and calls the configured routing provider but never writes
listings, assessments, accounts, or recommendation runs. A routing outage marks
the evaluation incomplete instead of recording false zero metrics.

The current evaluation uses a small controlled set of development tenant
profiles and manually/independently assigned relevance judgments over the
seeded DhakaNest inventory. Results therefore demonstrate recommendation
behavior on the development benchmark, not universal real-world recommendation
performance.

## Recommendation History and Persistence

An explicit tenant request to `POST /api/recommendations/ranked` may include:

```text
X-Idempotency-Key: <one unique key for the tenant submission>
```

After Parts 1-6 complete successfully, the API stores one immutable snapshot in
the `recommendation_runs` collection. It contains the validated request,
ranking counts, normalized weights, scoring/KNN/routing metadata, and complete
backend-generated candidates including listing facts, image references, stored
rent assessments, scores, commutes, and explanations. The frontend never
supplies ranking data for persistence.

The unique key is scoped to the authenticated tenant. Reusing the same key
returns the original run without creating another record. Different tenants may
use the same key. Requests without the header remain backward compatible:
recommendations run normally but are not persisted. Validation,
authentication, routing, and recommendation failures create no history record;
a successful zero-result search is persisted.

Tenant-only history APIs are:

```text
GET /api/recommendations/history?page=1&page_size=10
GET /api/recommendations/history/{run_id}
```

List results are newest-first and page size is limited to 50. Detail lookup uses
both authenticated tenant ID and run ID, so another tenant receives the same
not-found behavior as an unknown or malformed ID. Landlord and admin users
cannot use these tenant routes.

Historical recommendation runs are snapshots of the listing and recommendation
data at the time the search was generated. Opening history does not rerun OSRM,
KNN, WSM, XGBoost, explanations, or any other recommendation calculation. The
core `get_ranked_recommendations` service remains free of history persistence,
so scripts and Recommendation Part 7 evaluation never create history records.

With FastAPI running locally, verify one idempotent development flow with:

```powershell
python scripts/check_recommendation_history.py
```

The script uses a fixed development key, so rerunning it reopens the same test
run instead of adding duplicate history records.
## Recommendation map and road-route visualization

Recommendation Part 9 uses the existing OSRM Table API measurements for
recommendation commute metrics and the OSRM Route API only for on-demand map
polylines. The visualization endpoint is:

```text
GET /api/recommendations/history/{run_id}/listings/{listing_id}/route-geometry
```

It is tenant-only and reads the selected home and destination coordinates from
the immutable recommendation-run snapshot. It never looks up the current
listing or reruns filtering, KNN, WSM, or rent prediction. A failed individual
destination route is omitted while other routes are returned; a provider
outage returns `503` without affecting saved recommendation results.

Historical distance and duration values are the metrics saved when the run was
generated. Route lines are traffic-free visualization geometry generated on
demand from saved coordinates. The public OSRM server is suitable for light
development use and has no production SLA.

With FastAPI running and at least one saved recommendation run available, check
the map route endpoint with:

```powershell
python scripts/check_recommendation_map.py
```

## Local Routing Reliability

Recommendation services now depend on a provider-neutral routing interface.
The configured primary adapter handles both matrix and route-geometry calls; an
optional fallback adapter can repeat the entire logical operation after a
primary outage. Results from different providers are never combined inside one
matrix or geometry batch, and no straight-line or guessed commute fallback is
used.

The default `https://router.project-osrm.org` endpoint is public development and
demo infrastructure with no production SLA. Production should set
`ROUTING_BASE_URL` to a self-hosted OSRM instance or implement a contracted
provider adapter behind the same interface.

Routing configuration includes the primary and optional fallback provider/base
URL, a 10-second provider timeout, one bounded transient retry with short
exponential backoff, separate matrix and geometry TTLs, a bounded in-process
LRU/TTL cache, and circuit-breaker threshold/recovery settings. Coordinates are
rounded to six decimals for deterministic cache keys; actual provider request
coordinates are unchanged. Identical concurrent requests are coalesced into one
provider call. This process-local design is suitable for one backend process;
multi-instance deployment should replace the cache/limiter abstractions with a
shared implementation when consistent cross-instance limits are required.

Tenant-based process-local limits protect `POST /api/recommendations/ranked`
and the saved-run route-geometry endpoint. Existing idempotent ranked responses
are returned before consuming limiter/provider capacity. An exceeded limit
returns `429` with `Retry-After`; endpoint requests count even when their route
result is cached, so HTTP abuse and upstream demand remain separate concerns.

Every response receives a bounded `X-Request-ID`, and routing operations emit
safe structured logs containing provider, operation, cache/fallback state,
attempt, duration, status, and error category. `GET /health/routing` exposes
only process-local routing health and aggregate counters. It never exposes
tenant data, credentials, tokens, or upstream URLs.

Local runtime checks can use:

```text
GET /health  - liveness; the FastAPI process is running
GET /ready   - readiness; MongoDB and at least one routing provider are usable
```

Liveness remains healthy during a routing outage. Readiness stays healthy when
the primary is down but a configured fallback passes its bounded health probe;
it returns `503` when MongoDB or every configured routing provider is unusable.
Provider health results are briefly cached to avoid excessive probe traffic.

Failure meanings remain distinct: no matching homes is a successful empty
recommendation, while routing unavailability is a service failure. Route
geometry unavailability affects only map polylines; cards, markers, stored
commute values, scores, reasons, ranks, and immutable historical snapshots stay
usable. Part 10 does not alter hard filters, destination scoring, KNN, WSM,
ranking tie-breaks, explanations, evaluation labels, or historical results.

The full safe configuration template is in `.env.example`. To inspect live
development cache behavior without creating a recommendation run, rerun:

```powershell
python scripts/check_recommendation_map.py
```

It times two identical route requests and reports cache miss/hit deltas. These
local numbers are diagnostic only and are not production throughput claims.

## Synthetic academic inventory

The local demo can use a deterministic, coverage-driven inventory of 2,500
approved listings plus 100 lifecycle examples. These records are synthetic
academic/demo data. They are not current Dhaka market listings, market samples,
or evidence about the real distribution of rents.

Run these commands from `backend/`:

```powershell
python scripts/seed_academic_inventory.py --dry-run
python scripts/seed_academic_inventory.py --apply
python scripts/seed_academic_inventory.py --report
python scripts/seed_academic_inventory.py --cleanup
```

The default seed is `20261005`; use `--seed` and `--count` for a reproducible
custom batch. Dry run validates records and writes the coverage report without
touching MongoDB. Apply bulk-inserts only missing deterministic seed keys, so
rerunning the same batch does not duplicate listings. Cleanup matches the
dedicated `academic_inventory_v1` marker and cannot delete manual listings.

Generation uses repository-verified micro-area anchors with small deterministic
coordinate jitter, the production XGBoost predictor as each rent baseline, and
the normal stored rent-assessment builder. Variation is stratified into
competition groups spanning property type, furnishing, size, amenities, and
fairness bands. Empty image arrays use the application's placeholder behavior;
the script performs no Cloudinary uploads or external geocoding.

Estimated travel cost and estimated monthly spend are not stored in seeded
listings. They remain tenant-specific recommendation-time calculations based on
OSRM distance, destinations, and travel frequency.
