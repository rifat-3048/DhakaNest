from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# These role values are the only roles DhakaNest currently understands.
UserRole = Literal["tenant", "landlord", "admin"]


class UserRegister(BaseModel):
    """Request body for creating a new tenant or landlord account."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=20)
    password: str = Field(..., min_length=6, max_length=128)

    # The service layer blocks public admin registration with a clear error.
    role: UserRole


class UserLogin(BaseModel):
    """Request body for logging in with email and password."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User data returned by the API.

    Notice that password_hash is intentionally not included here.
    """

    id: str
    name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole
    is_active: bool


class RegisterResponse(BaseModel):
    """Response returned after successful registration."""

    message: str
    user: UserResponse


class LoginUserResponse(BaseModel):
    """Smaller user object returned together with a login token."""

    id: str
    name: str
    email: EmailStr
    role: UserRole


class TokenResponse(BaseModel):
    """Response returned after a successful login."""

    access_token: str
    token_type: str = "bearer"
    user: LoginUserResponse
