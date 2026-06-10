from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.database import get_database
from app.schemas.user_schema import (
    RegisterResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import (
    login_user,
    register_user,
    user_document_to_response,
)


# All routes in this file start with /auth.
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse)
async def register(user_data: UserRegister) -> RegisterResponse:
    """Create a new tenant or landlord account."""
    database = get_database()
    user = await register_user(database, user_data)

    return RegisterResponse(
        message="User registered successfully",
        user=user,
    )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin) -> TokenResponse:
    """Login with email and password, then return a JWT token."""
    database = get_database()
    return await login_user(database, login_data.email, login_data.password)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently logged-in user."""
    return user_document_to_response(current_user)
