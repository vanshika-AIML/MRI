"""Authentication API routes — Phase 9.

Exposes:
  POST /api/v1/auth/register   — create account
  POST /api/v1/auth/login      — obtain JWT tokens
  POST /api/v1/auth/refresh    — refresh access token
  POST /api/v1/auth/logout     — client-side token invalidation notice
  GET  /api/v1/auth/me         — current user profile
  PATCH /api/v1/auth/me        — update profile / change password
  PUT  /api/v1/auth/users/{id}/role  — admin: change user role
"""

from typing import Optional
from app.core.rate_limit import limiter
from app.core.config import settings

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_audit_logger,
    get_current_user,
    get_db_optional,
    require_role,
    AuditLogger,
)
from app.schemas.auth import (
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserPublicResponse,
    UserRegisterRequest,
    UserUpdateRequest,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

_NO_DB_DETAIL = (
    "Authentication requires a database connection. "
    "DATABASE_URL is not configured or the database is unreachable."
)


def _require_db(db: Optional[Session]) -> Session:
    """Raise 503 if DB is unavailable (auth is always DB-dependent)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_NO_DB_DETAIL,
        )
    return db


# ==============================================================================
# Registration
# ==============================================================================

@router.post(
    "/register",
    response_model=UserPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Create a new user with 'viewer' role by default (least-privilege). "
        "Email and username must be unique."
    ),
    responses={
        201: {"description": "Account created"},
        400: {"description": "Validation error or duplicate email/username"},
        503: {"description": "Database unavailable"},
    },
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(
    data: UserRegisterRequest,
    request: Request,
    db: Optional[Session] = Depends(get_db_optional),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Register a new user account."""
    db = _require_db(db)
    svc = AuthService(db)

    try:
        user, _ = svc.register(data)
        audit.log(
            action="auth.register",
            user_id=str(user.id),
            resource_type="user",
            resource_id=str(user.id),
            outcome="success",
            details={"username": user.username, "role": user.role},
        )
        return UserPublicResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            profession=user.profession,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )
    except ValueError as exc:
        audit.log(
            action="auth.register",
            outcome="failure",
            details={"reason": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ==============================================================================
# Login
# ==============================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain JWT access and refresh tokens",
    description=(
        "Authenticate with email and password to receive a Bearer access token "
        "and a refresh token.  Access tokens expire after 60 minutes by default."
    ),
    responses={
        200: {"description": "Authentication successful"},
        401: {"description": "Invalid credentials or account locked"},
        503: {"description": "Database unavailable"},
    },
)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    data: UserLoginRequest,
    request: Request,
    db: Optional[Session] = Depends(get_db_optional),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Authenticate user and return JWT tokens."""
    db = _require_db(db)
    svc = AuthService(db)

    user = svc.authenticate(data.email, data.password)
    if user is None:
        audit.log(
            action="auth.login_failure",
            outcome="failure",
            # Do NOT log the attempted email in audit details to avoid PII leakage
        )
        db.commit()  # Persist lockout counters and audit before returning 401.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account is locked. Please try again later.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = svc.issue_tokens(user)
    audit.log(
        action="auth.login_success",
        user_id=str(user.id),
        resource_type="user",
        resource_id=str(user.id),
        outcome="success",
    )
    return tokens


# ==============================================================================
# Token refresh
# ==============================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
    description="Exchange a valid refresh token for a new access + refresh token pair.",
    responses={
        200: {"description": "Tokens refreshed"},
        401: {"description": "Invalid or expired refresh token"},
        503: {"description": "Database unavailable"},
    },
)
async def refresh(
    data: TokenRefreshRequest,
    db: Optional[Session] = Depends(get_db_optional),
):
    """Refresh access token using a valid refresh token."""
    db = _require_db(db)
    svc = AuthService(db)

    try:
        return svc.refresh_tokens(data.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==============================================================================
# Logout (client-side notice)
# ==============================================================================

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (client-side token revocation notice)",
    description=(
        "Informs the server of logout intent. "
        "The client MUST discard both the access and refresh tokens. "
        "Server-side logout revokes all outstanding tokens for this account."
    ),
)
async def logout(
    db: Optional[Session] = Depends(get_db_optional),
    current_user: dict = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Logout endpoint — client must discard stored tokens."""
    db = _require_db(db)
    user = AuthService(db).get_user_by_id(current_user["sub"])
    user.token_version += 1
    db.flush()
    audit.log(
        action="auth.logout",
        user_id=current_user.get("sub"),
        resource_type="user",
        resource_id=current_user.get("sub"),
        outcome="success",
    )
    return {
        "message": "Logged out successfully. Please discard your access and refresh tokens."
    }


# ==============================================================================
# Current user profile
# ==============================================================================

@router.get(
    "/me",
    response_model=UserPublicResponse,
    summary="Get current user profile",
    description="Returns the authenticated user's profile. Requires Bearer token.",
    responses={
        200: {"description": "User profile returned"},
        401: {"description": "Not authenticated"},
        503: {"description": "Database unavailable"},
    },
)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: Optional[Session] = Depends(get_db_optional),
):
    """Return the authenticated user's profile."""
    db = _require_db(db)
    svc = AuthService(db)

    user = svc.get_user_by_id(current_user["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return UserPublicResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        profession=user.profession,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


@router.patch(
    "/me",
    response_model=UserPublicResponse,
    summary="Update current user profile",
    description=(
        "Update your display name or change your password. "
        "Password changes require the current_password to be provided."
    ),
    responses={
        200: {"description": "Profile updated"},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        503: {"description": "Database unavailable"},
    },
)
async def update_me(
    data: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Optional[Session] = Depends(get_db_optional),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Update current user's profile or password."""
    db = _require_db(db)
    svc = AuthService(db)

    try:
        user = svc.update_profile(current_user["sub"], data)
        audit.log(
            action="user.profile_update",
            user_id=str(user.id),
            resource_type="user",
            resource_id=str(user.id),
            outcome="success",
            details={"changed_fields": [k for k, v in data.model_dump().items() if v is not None]},
        )
        return UserPublicResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            profession=user.profession,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ==============================================================================
# Admin: role management
# ==============================================================================

@router.put(
    "/users/{user_id}/role",
    response_model=UserPublicResponse,
    summary="Change a user's role (admin only)",
    description=(
        "Assign a new role to a user account. "
        "Valid roles: viewer, radiologist, admin."
    ),
    responses={
        200: {"description": "Role updated"},
        400: {"description": "Invalid role"},
        401: {"description": "Not authenticated"},
        403: {"description": "Requires admin role"},
        404: {"description": "User not found"},
        503: {"description": "Database unavailable"},
    },
)
async def change_user_role(
    user_id: str,
    role: str,
    current_user: dict = Depends(require_role("admin")),
    db: Optional[Session] = Depends(get_db_optional),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Admin: change a user's role."""
    db = _require_db(db)
    svc = AuthService(db)

    try:
        user = svc.change_role(user_id, role, actor_id=current_user["sub"])
        audit.log(
            action="user.role_change",
            user_id=current_user["sub"],
            resource_type="user",
            resource_id=user_id,
            outcome="success",
            details={"new_role": role},
        )
        return UserPublicResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            profession=user.profession,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
