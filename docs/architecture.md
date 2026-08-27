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
-> location, budget, space, amenities, rent-fairness WSM
-> deterministic ranking and explanations
-> current results, selected-home route map, immutable history
```

Property similarity selects the KNN candidate set; it is not a sixth WSM
criterion. Route geometry visualizes a saved recommendation and never changes
stored commute metrics, scores, or rank. Household size remains descriptive.
There is no tenant residential-area selector: destinations drive location fit.

No container or cloud layer is required for the supported local academic run.
