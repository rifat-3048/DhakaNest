# DhakaNest Backend

This folder contains the FastAPI backend for DhakaNest.

## What Exists Now

- A FastAPI app with health and database health endpoints.
- Environment-based configuration using `pydantic-settings`.
- MongoDB connection setup using Motor.
- Authentication for tenant, landlord, and admin users.
- Public registration for tenant and landlord users only.
- JWT login, current-user lookup, and role-based support.
- A complete landlord listing and admin review lifecycle.
- Base recommendation eligibility and tenant hard-filter candidate retrieval.

## What Will Be Added Later

- Destination-aware commute scoring.
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
transport, or walking conditions. A production deployment should configure a
self-hosted or contracted routing provider with an appropriate service level.

To run the read-only commute scenarios against local listings:

```powershell
python scripts/check_recommendation_commutes.py
```

The script uses Nominatim-verified Dhaka destination coordinates, calls routing,
prints aggregate and per-candidate measurements, and never changes MongoDB data.
