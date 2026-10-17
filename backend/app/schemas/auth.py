"""Pydantic schemas for authentication and user management API."""
import re
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.config import settings

UserProfession = Literal[
    "radiologist",
    "physician",
    "medical_student",
    "researcher",
    "viewer",
]


# ---------------------------------------------------------------------------
# Registration / Login request schemas
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """Schema for POST /api/v1/auth/register."""

    email: EmailStr = Field(..., description="Valid email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Display name (3-32 chars, alphanumeric/underscore/hyphen)",
    )
    password: str = Field(
        ...,
        min_length=settings.MIN_PASSWORD_LENGTH,
        max_length=128,
        description="Password — minimum 8 characters",
    )
    full_name: Optional[str] = Field(None, max_length=255, description="Optional display name")
    profession: UserProfession = Field(
        "viewer",
        description="Self-declared profession; does not verify credentials or grant permissions",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Allow only alphanumeric, underscore, or hyphen characters."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError(
                "Username may only contain letters, digits, underscores, and hyphens"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce minimum complexity: at least one digit and one letter."""
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLoginRequest(BaseModel):
    """Schema for POST /api/v1/auth/login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")


class TokenRefreshRequest(BaseModel):
    """Schema for POST /api/v1/auth/refresh."""

    refresh_token: str = Field(..., description="Valid refresh token")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Returned by login and refresh endpoints."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(
        default=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        description="Access token lifetime in seconds",
    )
    role: str = Field(..., description="User role")


class UserPublicResponse(BaseModel):
    """Public user profile — never exposes password_hash or sensitive internals."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="Display name")
    role: str = Field(..., description="User role")
    profession: UserProfession = Field(
        "viewer", description="Self-declared profession; not credential verification"
    )
    is_active: bool = Field(..., description="Account active flag")
    is_verified: bool = Field(..., description="Email verified flag")

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Schema for PATCH /api/v1/auth/me — partial profile updates."""

    full_name: Optional[str] = Field(None, max_length=255)
    current_password: Optional[str] = Field(
        None,
        min_length=1,
        description="Required when changing password",
    )
    new_password: Optional[str] = Field(
        None,
        min_length=settings.MIN_PASSWORD_LENGTH,
        max_length=128,
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not any(c.isdigit() for c in v):
            raise ValueError("New password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("New password must contain at least one letter")
        return v
