# DhakaNest Local Runtime Baseline

DhakaNest runs locally on this computer. The Next.js frontend and FastAPI
backend use separate terminals and connect to the locally installed MongoDB
Server. No Docker or cloud deployment is required.

## Backend

From `D:\DhakaNest\backend`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run one backend process. Routing cache, rate limits, single-flight requests,
metrics, and circuit-breaker state are process-local.

```text
API:       http://127.0.0.1:8000
Docs:      http://127.0.0.1:8000/docs
Health:    http://127.0.0.1:8000/health
Readiness: http://127.0.0.1:8000/ready
```

## Frontend

Keep the backend terminal running. In a second terminal, from
`D:\DhakaNest\frontend`:

```powershell
npm run dev
```

Open `http://localhost:3000`. The local environment file should contain:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

To test the optimized frontend locally:

```powershell
npm run build
npm start
```

## Local Environment

Keep real MongoDB, JWT, and Cloudinary values only in `backend/.env`. Keep the
frontend API address only in `frontend/.env.local`. Both are ignored by Git.

Development mode permits explicit local frontend origins and trusted hosts. The
public OSRM endpoint is acceptable for light university development, but it has
no production SLA and must never be load-tested.

## Local Security Notes

Backend and frontend responses include basic security headers. JWTs continue to
use the Authorization header and browser localStorage. Full CSP and HTTPS
termination are deployment concerns and are not required for local-only use.
