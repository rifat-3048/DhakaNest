# Final API Route Inventory

OpenAPI generation was verified successfully. Important registered routes are:

## Health and Readiness

- `GET /health`
- `GET /health/db`
- `GET /health/routing`
- `GET /ready`

## Authentication

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

## Landlord Listings

- `POST /api/listings`
- `GET /api/listings/mine`
- `GET/PATCH /api/listings/{listing_id}`
- image upload, delete, primary-image, and reorder routes
- `POST /api/listings/{listing_id}/submit`
- `PATCH /api/listings/{listing_id}/mark-rented`

## Admin Review and Rent Assessment

- `GET /api/admin/listings`
- `GET /api/admin/listings/pending`
- `GET /api/admin/listings/{listing_id}`
- `POST /api/admin/listings/{listing_id}/check-rent-fairness`
- `PATCH /api/admin/listings/{listing_id}/decision`
- `POST /api/rent/predict`

## Recommendations, History, and Map

- staged candidate/commute/scoring/KNN diagnostic POST routes
- `POST /api/recommendations/ranked`
- `GET /api/recommendations/history`
- `GET /api/recommendations/history/{run_id}`
- `GET /api/recommendations/history/{run_id}/listings/{listing_id}/route-geometry`

All protected routes retain their existing JWT and role checks.
