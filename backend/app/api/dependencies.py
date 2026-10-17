"""FastAPI dependencies for API route handlers — Phase 9.

Provides:
  - get_db_optional: database session with graceful fallback
  - get_current_user: strict JWT authentication (raises 401)
  - get_current_user_optional: soft authentication (returns None if no token)
  - require_role: role-based access control guard
  - get_audit_logger: structured audit event recorder
"""

import logging
from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.security import verify_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


# ==============================================================================
# Database
# ==============================================================================

def get_db_optional() -> Generator[Optional[Session], None, None]:
    """Provide a database session if DATABASE_URL is configured and reachable.

    Probes connectivity before yielding so callers receive None — not a lazy
    Session that explodes on first query — when PostgreSQL is unreachable.
    """
    if not settings.DATABASE_URL:
        yield None
        return

    try:
        from app.db.session import SessionLocal, _init_engine

        # Ensure engine is initialised (idempotent)
        _init_engine()

        # Probe: acquire and immediately release a real connection.
        # This surfaces connection errors *here* (caught below) instead of
        # inside the endpoint handler where they would escape as 500s.
        from app.db.session import _engine as _eng
        if _eng is not None:
            with _eng.connect() as probe_conn:
                pass   # connection acquired and released cleanly

        db = SessionLocal()
    except Exception as err:
        logger.debug(f"Database unavailable: {err}")
        yield None
        return

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ==============================================================================
# Authentication
# ==============================================================================

def _extract_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    authorization_header: Optional[str],
) -> Optional[str]:
    """Extract raw token string from Bearer credentials or raw Authorization header."""
    if credentials and credentials.credentials:
        return credentials.credentials
    if authorization_header and authorization_header.lower().startswith("bearer "):
        return authorization_header[7:].strip()
    return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    authorization: Optional[str] = Header(None),
    db: Optional[Session] = Depends(get_db_optional),
) -> dict:
    """Require a valid JWT access token.  Raises 401 if absent or invalid.

    Returns:
        Decoded token payload dict with at minimum ``sub`` (user ID) and ``role``.

    Raises:
        HTTPException 401: Missing, invalid, or expired token.
    """
    token = _extract_token(credentials, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if db is None and settings.ENVIRONMENT == "production":
        raise HTTPException(503, "Account validation unavailable.")
    # Optionally verify user is still active in DB (when DB is available)
    if db is not None:
        try:
            from app.models.user import User
            from sqlalchemy import select
            user_id = payload.get("sub")
            if user_id:
                user = db.execute(
                    select(User).where(User.id == __import__("uuid").UUID(user_id))
                ).scalar_one_or_none()
                if user is None or not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Account not found or has been deactivated.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                if payload.get("ver", 0) != user.token_version:
                    raise HTTPException(401, "Token has been revoked.")
                payload["role"] = user.role
        except HTTPException:
            raise
        except Exception as db_err:
            raise HTTPException(503, "Account validation unavailable.") from db_err

    return payload


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    authorization: Optional[str] = Header(None),
    db: Optional[Session] = Depends(get_db_optional),
) -> Optional[dict]:
    if not authorization and not credentials:
        return None
    return get_current_user(credentials, authorization, db)


def require_role(*roles: str):
    """Dependency factory that enforces role-based access.

    Usage::
        @router.post("/admin/users")
        def admin_only(user: dict = Depends(require_role("admin"))):
            ...

    Args:
        *roles: One or more allowed role strings.

    Raises:
        HTTPException 403: User's role is not in the allowed list.
    """
    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {', '.join(roles)}. "
                    f"Your role: {user_role}."
                ),
            )
        return current_user
    return _check


# ==============================================================================
# Audit logging helper
# ==============================================================================

class AuditLogger:
    """Records security-relevant events to the audit_logs table when DB is available."""

    def __init__(self, db: Optional[Session], request: Optional[Request] = None):
        self._db = db
        self._request = request

    def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        outcome: str = "success",
        details: Optional[dict] = None,
    ) -> None:
        """Write an audit event.  Silently skips if DB is unavailable."""
        if self._db is None:
            logger.debug(
                f"Audit (no-db): action={action} user={user_id} outcome={outcome}"
            )
            return

        ip = None
        ua = None
        if self._request:
            # Respect X-Forwarded-For for proxied deployments
            forwarded = self._request.headers.get("X-Forwarded-For")
            ip = forwarded.split(",")[0].strip() if forwarded else str(
                self._request.client.host if self._request.client else ""
            )
            ua = (self._request.headers.get("User-Agent") or "")[:512]

        try:
            from app.models.audit_log import AuditLog
            import uuid as _uuid

            entry = AuditLog(
                user_id=_uuid.UUID(user_id) if user_id else None,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                ip_address=ip,
                user_agent=ua,
                outcome=outcome,
                details=details,
            )
            with self._db.begin_nested():
                self._db.add(entry)
                self._db.flush()
        except Exception as err:
            logger.warning("Audit log write failed (%s)", type(err).__name__)


def get_audit_logger(
    request: Request,
    db: Optional[Session] = Depends(get_db_optional),
) -> AuditLogger:
    """FastAPI dependency that returns a ready-to-use AuditLogger."""
    return AuditLogger(db=db, request=request)


# ---------------------------------------------------------------------------
# Backward-compatible stub for older route files
# ---------------------------------------------------------------------------

def verify_auth_header(
    authorization: Optional[str] = Header(None, description="Optional Bearer token or API key"),
) -> Optional[str]:
    """Validate API authorization headers when present (backward-compat stub)."""
    if authorization:
        logger.debug("Authorization header received in request")
    return authorization
