from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.security import decode_access_token
from app.database import get_database
from app.services.auth_service import get_user_by_id


# This reads the full Authorization header from requests.
# In Swagger UI, paste: Bearer your_access_token_here
authorization_header = APIKeyHeader(name="Authorization", auto_error=False)


async def get_current_user(
    authorization: str | None = Depends(authorization_header),
) -> dict:
    """Return the logged-in user from the Bearer token."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token.",
        )

    token = authorization.replace("Bearer ", "", 1).strip()
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    database = get_database()
    user = await get_user_by_id(database, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


def require_role(required_role: str) -> Callable:
    """Create a dependency that only allows users with one specific role.

    Later routes can use this for landlord-only, tenant-only, or admin-only APIs.
    """

    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only {required_role} users can access this route.",
            )

        return current_user

    return role_checker
