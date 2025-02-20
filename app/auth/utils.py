from random import random
import string
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def generate_random_password(length: int = 12) -> str:
    """
    Generate a random password with a mix of letters, digits, and symbols.
    """
    characters = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(random.choice(characters) for _ in range(length))


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    utc_now = datetime.now(timezone.utc)
    if expires_delta:
        expire = utc_now + expires_delta
    else:
        expire = utc_now + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_password_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def create_password_reset_email(reset_url: str) -> str:
    """Create the password reset email body."""
    return f"""
Hello,

You have requested to reset your password. Please click the link below to reset your password:

{reset_url}

If you didn't request this, please ignore this email.

This link will expire in 30 minutes.

Best regards,
YourEmailValidator Team
    """
