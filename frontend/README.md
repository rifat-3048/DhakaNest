# DhakaNest Frontend

This folder contains the Next.js frontend for DhakaNest.

## Current Features

- Home page.
- Register page for tenant and landlord users.
- Login page.
- Protected dashboards for tenant, landlord, and admin roles.
- Local JWT token storage for development.
- Tenant housing and important-destination preference form.
- Ranked, explainable tenant recommendations with commute and criterion details.
- Responsive recommendation cards with safe missing-image placeholders.

## Tenant Recommendation Flow

```text
Tenant Preference Form
-> POST /api/recommendations/ranked
-> /tenant/recommendations
-> ranked recommendation details
```

The backend is the source of truth for scores and rank. The frontend displays
`final_suitability_score` as a Suitability percentage and never recalculates the
Weighted Sum Model. Suitability is not model confidence, probability, or
classification accuracy.

Commute durations are shown as estimated drives. They are traffic-free OSRM road
estimates, not live Dhaka traffic times. Listings without images use a local
placeholder instead of a broken or externally hotlinked image.

Each explicit tenant form submission creates one browser UUID and sends it as
`X-Idempotency-Key` to the ranked API. The results page reuses that UUID for a
retry or refresh, while a new explicit form submission creates a new UUID.
Successful results remain available immediately through session storage and are
also stored durably by the backend.

Tenant recommendation history is available at:

```text
/tenant/recommendations/history
/tenant/recommendations/history/[runId]
```

The list shows generated time, destinations, budget, recommendation count, and
top suitability. The detail page fetches the immutable backend snapshot and
reuses recommendation cards for stored ranks, criterion scores, commute
estimates, explanations, and image fallbacks. Refreshing a historical URL works
without session storage and never calls the ranked recommendation endpoint.

## Local Development

Create a local environment file from `.env.local.example`, then run the Next.js development server.

## Production Build

Set `NEXT_PUBLIC_API_BASE_URL` to the public HTTPS FastAPI origin before running
`npm run build`. Production builds fail when this variable is absent. For local
production-mode testing, run `npm run build` followed by `npm start`. See
`../docs/deployment.md` for the local runtime baseline.
## Recommendation maps

Current and historical recommendation results use `Leaflet` and
`react-leaflet` with OpenStreetMap raster tiles. OpenStreetMap attribution
remains visible and no map API key is required.

The map displays numbered ranked-home markers and distinct important-destination
markers. Only the selected home requests OSRM Route API geometry, and results
are cached in memory by recommendation run and listing ID. Recommendation
commute metrics continue to come from the saved recommendation snapshot; the
route polyline is traffic-free visualization generated on demand. The public
OSRM service has no production SLA.
