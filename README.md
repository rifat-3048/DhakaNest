# DhakaNest

DhakaNest is a location-aware rental home recommendation system for Dhaka City.
It is a local academic project with separate tenant, landlord, and admin flows.

## Technology

- Next.js, TypeScript, Tailwind CSS, Leaflet, and OpenStreetMap
- FastAPI, Python, Motor, and MongoDB
- Cloudinary listing-image storage
- XGBoost rent assessment
- OSRM road routing
- Content-based KNN, cosine similarity, and a five-criterion Weighted Sum Model

## Main Workflows

- **Tenant:** define housing requirements and 1-3 important destinations, receive
  ranked explanations and commute details, view the map, and reopen immutable
  recommendation history.
- **Landlord:** create and edit a draft, manage images, submit it for review, and
  mark an approved home as rented.
- **Admin:** inspect submitted listings, run the stored XGBoost rent-fairness
  assessment, and approve, reject, or request revision.

```text
Eligibility -> Hard filters -> OSRM routing -> Destination scoring
-> Content-based KNN -> Five-criterion WSM -> Ranking
-> Deterministic reasons -> Results, map, and history
```

## Run Locally

Start MongoDB Server first. In a backend terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000`. API documentation is at
`http://127.0.0.1:8000/docs`; liveness and readiness are `/health` and `/ready`.
Copy the backend and frontend example environment files to local ignored files
and provide real local values. Never commit `.env` or `.env.local`.

## Verify

From `backend/`:

```powershell
python -m unittest discover -s tests
python scripts/evaluate_recommendations.py
python scripts/final_preflight_check.py
python scripts/final_acceptance_check.py
```

From `frontend/`:

```powershell
npm test
npx tsc --noEmit
npm run lint
npm run build
```

See [local setup](docs/local-setup.md), the [command reference](docs/final-command-reference.md),
and the [submission manifest](docs/submission-manifest.md).

## Important Limits

OSRM values are traffic-free road estimates. The recommendation benchmark is a
small controlled development set with manually assigned relevance judgments.
Household size is descriptive only, and some development listings may use image
placeholders. DhakaNest is intended for local university demonstration; Docker
and cloud hosting are outside the current scope.
