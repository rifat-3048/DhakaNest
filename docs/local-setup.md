# Local Setup

## Prerequisites

- Windows PowerShell
- Python 3.12 and Node.js 22-compatible tooling
- locally installed MongoDB Server (Compass is the optional GUI)
- Cloudinary credentials for listing-image operations
- internet access to the configured OSRM endpoint and map/geocoding services

## Backend

From `backend/`, create and activate the virtual environment, then install the
requirements if needed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set local MongoDB, JWT, and Cloudinary values.
The exported XGBoost bundle must remain under
`app/ml/artifacts/dhakanest_xgboost_v1/`. Start MongoDB Server, then run:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend

From `frontend/`, install dependencies if needed, copy `.env.local.example` to
`.env.local`, and keep the local API address as `http://127.0.0.1:8000`.

```powershell
npm install
npm run dev
```

Open `http://localhost:3000` and verify `http://127.0.0.1:8000/health`,
`/ready`, and `/docs`. Use two terminals; the helper scripts are optional.

Real secrets and demo passwords belong only in ignored local files. Docker and
cloud deployment are not part of this setup.
