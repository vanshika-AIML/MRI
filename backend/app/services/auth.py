"""Authentication service — registration, login, token management."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    MAX_FAILED_LOGIN_ATTEMPTS,
    ACCOUNT_LOCKOUT_MINUTES,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserPublicResponse,
    UserRegisterRequest,
    UserUpdateRequest,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Domain service for authentication operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, data: UserRegisterRequest) -> Tuple[User, str]:
        """Create a new user account.

        Returns:
            Tuple of (created User, raw message).

        Raises:
            ValueError: Email or username already in use, or validation error.
        """
        # Check email uniqueness (case-insensitive)
        existing_email = self.db.execute(
            select(User).where(User.email == data.email.lower())
        ).scalar_one_or_none()
        if existing_email is not None:
            raise ValueError("An account with this email address already exists.")

        # Check username uniqueness
        existing_username = self.db.execute(
            select(User).where(User.username == data.username.lower())
        ).scalar_one_or_none()
        if existing_username is not None:
            raise ValueError("This username is already taken.")

        user = User(
            email=data.email.lower(),
            username=data.username.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role="viewer",       # Least-privilege default
            profession=data.profession,
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        self.db.flush()  # Populate id before returning
        logger.info("New user registered")
        return user, "Registration successful"

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Verify credentials and return authenticated User or None.

        Implements:
          - Case-insensitive email lookup
          - Account lockout after MAX_FAILED_LOGIN_ATTEMPTS
          - Failed attempt counter reset on success
          - Never reveals whether email exists or password is wrong (generic error)
        """
        user: Optional[User] = self.db.execute(
            select(User).where(User.email == email.lower())
        ).scalar_one_or_none()

        if user is None:
            # Constant-time stub to prevent user enumeration via timing
            hash_password("dummy_prevent_timing_attack")
            logger.warning("Login attempt for unknown account")
            return None

        if not user.is_active:
            logger.warning(f"Login attempt for inactive account: user_id={user.id}")
            return None

        # Brute-force check
        now = self._utcnow()
        if user.locked_until and user.locked_until > now:
            logger.warning(
                f"Login attempt for locked account: user_id={user.id} locked_until={user.locked_until}"
            )
            return None

        if not verify_password(password, user.password_hash):
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= MAX_FAILED_LOGIN_ATTEMPTS:
                from datetime import timedelta
                user.locked_until = now + timedelta(minutes=ACCOUNT_LOCKOUT_MINUTES)
                logger.warning(
                    f"Account locked after {MAX_FAILED_LOGIN_ATTEMPTS} failed attempts: "
                    f"user_id={user.id}"
                )
            self.db.flush()
            return None

        # Success — reset counters
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        self.db.flush()
        return user

    def issue_tokens(self, user: User) -> TokenResponse:
        """Generate access + refresh tokens for an authenticated user."""
        user_id = str(user.id)
        access = create_access_token(subject=user_id, role=user.role, extra_claims={"ver": user.token_version})
        refresh = create_refresh_token(subject=user_id, role=user.role, token_version=user.token_version)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            role=user.role,
        )

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Validate a refresh token and issue new token pair.

        Raises:
            ValueError: Invalid, expired, or wrong token type.
        """
        from jwt import InvalidTokenError as JWTError
        try:
            payload = decode_token(refresh_token)
        except JWTError as exc:
            raise ValueError(f"Invalid refresh token: {exc}") from exc

        if payload.get("type") != "refresh":
            raise ValueError("Provided token is not a refresh token.")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Malformed token: missing subject.")

        user: Optional[User] = self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id)).with_for_update()
        ).scalar_one_or_none()

        if user is None or not user.is_active:
            raise ValueError("User account not found or is deactivated.")

        if payload.get("ver", 0) != user.token_version:
            raise ValueError("Refresh token has been revoked.")
        user.token_version += 1
        self.db.flush()
        return self.issue_tokens(user)

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Fetch user by UUID string."""
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None
        return self.db.execute(
            select(User).where(User.id == uid)
        ).scalar_one_or_none()

    def update_profile(self, user_id: str, data: UserUpdateRequest) -> User:
        """Update user profile fields.

        Raises:
            ValueError: User not found, wrong current password.
        """
        user = self.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User not found.")

        if data.full_name is not None:
            user.full_name = data.full_name

        if data.new_password is not None:
            if not data.current_password:
                raise ValueError("current_password is required to set a new password.")
            if not verify_password(data.current_password, user.password_hash):
                raise ValueError("Current password is incorrect.")
            user.password_hash = hash_password(data.new_password)
            user.token_version += 1
            logger.info(f"Password changed: user_id={user.id}")

        self.db.flush()
        return user

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def change_role(self, user_id: str, new_role: str, actor_id: str) -> User:
        """Change user role (admin only — enforced by route dependency).

        Raises:
            ValueError: Invalid role or user not found.
        """
        allowed_roles = {"viewer", "radiologist", "admin"}
        if new_role not in allowed_roles:
            raise ValueError(
                f"Invalid role '{new_role}'. Allowed: {', '.join(sorted(allowed_roles))}"
            )

        user = self.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User not found.")

        old_role = user.role
        user.role = new_role
        self.db.flush()
        logger.info(
            f"Role change: user_id={user_id} {old_role} → {new_role} by actor={actor_id}"
        )
        return user
