"""Authentication and security utilities — Phase 9.

Uses bcrypt directly (bypassing passlib which has bcrypt 5.x incompatibility).
JWT via python-jose.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from jwt import InvalidTokenError as JWTError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brute-force constants
# ---------------------------------------------------------------------------
MAX_FAILED_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_MINUTES = 30

# ---------------------------------------------------------------------------
# Password hashing — bcrypt directly (passlib 1.7.x is incompatible w/ bcrypt 5)
# ---------------------------------------------------------------------------
_BCRYPT_ROUNDS = 12  # OWASP recommendation


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain* password.

    Raises:
        ValueError: If plain exceeds 72 bytes (bcrypt hard limit).
    """
    raw = plain.encode("utf-8")
    if len(raw) > 72:
        raise ValueError(
            "Password is too long (maximum 72 bytes). "
            "Please use a shorter password."
        )
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(raw, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*.  Never raises."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    subject: str,
    role: str,
    extra_claims: Optional[dict] = None,
) -> str:
    """Issue a signed JWT access token.

    Args:
        subject:  User ID string (UUID hex).
        role:     User role string.
        extra_claims: Optional additional payload claims.

    Returns:
        Signed JWT string.  Expires after ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    now = _utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, role: str, token_version: int = 0) -> str:
    """Issue a long-lived signed JWT refresh token."""
    now = _utcnow()
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "ver": token_version,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Raises:
        JWTError: If token is invalid, expired, or tampered.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp", "sub", "iat"]})


def verify_access_token(token: str) -> Optional[dict]:
    """Return decoded token payload or None if invalid/expired.

    Safe to use in optional-auth contexts — does not raise.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
