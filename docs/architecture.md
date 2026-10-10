# DhakaNest Final Architecture

DhakaNest runs locally as a Next.js frontend and FastAPI backend. FastAPI uses
Motor to access MongoDB, Cloudinary to store listing images, an exported XGBoost
bundle for rent assessment, and OSRM for traffic-free road routing.

```text
Next.js frontend
  |-- tenant preferences, results, map, history
  |-- landlord listing workflow
  `-- admin review workflow
             |
             v
FastAPI API -- JWT role guards -- MongoDB
  |              |-- users
  |              |-- listings + stored rent assessments
  |              `-- immutable recommendation_runs
  |-- Cloudinary: listing image upload/delete
  |-- XGBoost: five-feature rent prediction at admin assessment time
  `-- OSRM: listing-to-destination table metrics and selected-home route geometry
```

## Recommendation Pipeline

```text
Tenant requirements + 1-3 destinations
-> approved, available, coordinate-valid eligibility
-> hard filters
-> OSRM road routing and optional commute constraints
-> importance-weighted destination access score
-> content-based KNN and cosine similarity
-> effective top-K candidate set
-> monthly travel-cost estimation from stored OSRM Table road distance
-> advertised rent + travel cost as estimated monthly spend
-> advertised-rent Budget Suitability against the maximum rent budget
-> location, budget, space, amenities, rent-fairness WSM
-> deterministic ranking and explanations
-> current results, selected-home route map, immutable history
```

Property similarity selects the KNN candidate set; it is not a sixth WSM
criterion. Route geometry visualizes a saved recommendation and never changes
stored commute metrics, scores, or rank. Household size remains descriptive.
There is no tenant residential-area selector: destinations drive location fit.

Preferred floor size is a soft structural target. It is not applied as a hard
minimum or maximum: it supplies the KNN area target and a symmetric proximity
component inside the existing WSM space score. Explicit legacy min/max area
fields remain backward-compatible hard bounds when an older caller sends them.

For complete new requests, each destination supplies travel days per month.
DhakaNest assumes one round trip per travel day and sums `one-way road distance
* 2 * days * configured BDT/km`. This advisory travel estimate is added to
advertised rent for the displayed estimated monthly spend, but neither travel
cost nor total spend enters Budget Suitability directly. Budget Suitability is
`clamp(1 - advertised rent / maximum rent budget, 0, 1)`. Importance remains a
location signal, KNN remains structural, and XGBoost rent fairness remains
independent. Incomplete requests do not claim a partial travel total.

No container or cloud layer is required for the supported local academic run.

## Local Academic Inventory

`scripts/seed_academic_inventory.py` can create 2,500 recommendation-ready
synthetic listings and 100 lifecycle examples for local demonstrations. It uses
trusted repository anchors with small deterministic jitter and production-model
rent assessments. Dedicated seed keys make apply idempotent and cleanup
synthetic-only. Its machine-readable coverage matrix is stored at
`backend/data/academic_inventory_coverage.json`.

The eligible inventory read ceiling is 5,000 records. After tenant hard
filtering, OSRM Table requests are split into deterministic batches of at most
75 listing coordinates plus up to three destinations. Batch results are merged
in original candidate order; any failed batch fails the complete matrix. No
straight-line fallback or recommendation-score change is introduced.
