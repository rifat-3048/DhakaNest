from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


# These role values are the only roles DhakaNest currently understands.
UserRole = Literal["tenant", "landlord", "admin"]


class UserRegister(BaseModel):
    """Request body for creating a new tenant or landlord account."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=11, max_length=11)
    password: str = Field(..., min_length=8, max_length=72)

    # The service layer blocks public admin registration with a clear error.
    role: UserRole

    @field_validator("phone")
    @classmethod
    def validate_bangladeshi_phone(cls, phone: str) -> str:
        """Accept only valid Bangladeshi mobile numbers in local format."""
        allowed_prefixes = ("013", "014", "015", "016", "017", "018", "019")

        if not phone.isdigit():
            raise ValueError("Phone number must contain digits only.")
        if len(phone) != 11:
            raise ValueError("Phone number must be exactly 11 digits long.")
        if not phone.startswith(allowed_prefixes):
            raise ValueError(
                "Phone number must start with 013, 014, 015, 016, 017, 018, or 019."
            )

        return phone

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        """Keep backend password rules the same as the register form."""
        missing_rules = []

        if len(password) < 8:
            missing_rules.append("minimum 8 characters")
        if len(password.encode("utf-8")) > 72:
            missing_rules.append("maximum 72 bytes")
        if not any(character.isupper() for character in password):
            missing_rules.append("one uppercase letter")
        if not any(character.islower() for character in password):
            missing_rules.append("one lowercase letter")
        if not any(character.isdigit() for character in password):
            missing_rules.append("one number")
        if not any(not character.isalnum() for character in password):
            missing_rules.append("one special character")

        if missing_rules:
            raise ValueError(
                "Password must include " + ", ".join(missing_rules) + "."
            )

        return password


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
