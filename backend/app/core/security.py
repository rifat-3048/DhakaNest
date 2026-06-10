from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


# passlib manages password hashing. bcrypt is a strong default for passwords.
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain password before saving it to MongoDB."""
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check whether a plain password matches a stored password hash."""
    return password_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    """Create a JWT access token for a user ID."""
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> str | None:
    """Decode a JWT token and return the user ID stored in the subject."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")

        if not isinstance(user_id, str):
            return None

        return user_id
    except JWTError:
        return None
