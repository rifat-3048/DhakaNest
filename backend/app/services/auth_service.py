from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.user_schema import TokenResponse, UserRegister, UserResponse
from app.utils.object_id import object_id_to_str


def user_document_to_response(user: dict) -> UserResponse:
    """Convert a MongoDB user document into the public API response shape."""
    return UserResponse(
        id=object_id_to_str(user["_id"]),
        name=user["name"],
        email=user["email"],
        phone=user.get("phone"),
        role=user["role"],
        is_active=user["is_active"],
    )


async def get_user_by_email(
    database: AsyncIOMotorDatabase,
    email: str,
) -> dict | None:
    """Find one user by email address."""
    return await database.users.find_one({"email": email.lower()})


async def get_user_by_id(
    database: AsyncIOMotorDatabase,
    user_id: str,
) -> dict | None:
    """Find one user by MongoDB ObjectId string."""
    if not ObjectId.is_valid(user_id):
        return None

    return await database.users.find_one({"_id": ObjectId(user_id)})


async def register_user(
    database: AsyncIOMotorDatabase,
    user_data: UserRegister,
) -> UserResponse:
    """Create a new tenant or landlord account."""
    existing_user = await get_user_by_email(database, user_data.email)

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    # A public request can only create tenant or landlord users.
    # The schema already validates this, and this check keeps the rule obvious.
    if user_data.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public admin registration is not allowed.",
        )

    now = datetime.now(timezone.utc)
    user_document = {
        "name": user_data.name,
        "email": user_data.email.lower(),
        "phone": user_data.phone,
        "password_hash": hash_password(user_data.password),
        "role": user_data.role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    result = await database.users.insert_one(user_document)
    created_user = await database.users.find_one({"_id": result.inserted_id})

    return user_document_to_response(created_user)


async def login_user(
    database: AsyncIOMotorDatabase,
    email: str,
    password: str,
) -> TokenResponse:
    """Verify login details and return a JWT access token."""
    user = await get_user_by_email(database, email)

    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    user_id = object_id_to_str(user["_id"])
    access_token = create_access_token(subject=user_id)

    return TokenResponse(
        access_token=access_token,
        user={
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    )
