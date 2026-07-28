# DhakaNest Backend

This folder contains the FastAPI backend for DhakaNest.

## What Exists Now

- A FastAPI app with health and database health endpoints.
- Environment-based configuration using `pydantic-settings`.
- MongoDB connection setup using Motor.
- Authentication for tenant, landlord, and admin users.
- Public registration for tenant and landlord users only.
- JWT login, current-user lookup, and role-based support.

## What Will Be Added Later

- Rental listing APIs.
- Recommendation APIs.
- Database models and schemas.
- Business services and utility helpers.

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
