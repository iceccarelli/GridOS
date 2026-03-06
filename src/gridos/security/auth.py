"""
Authentication and authorisation for GridOS.

Provides API key validation, JWT token creation/verification, and
FastAPI dependency functions for securing endpoints.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ── API Key Authentication ──────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In production, load from database or secrets manager
_VALID_API_KEYS: dict[str, dict[str, Any]] = {}


def register_api_key(key: str, name: str, roles: list[str] | None = None) -> str:
    """Register an API key.

    Parameters
    ----------
    key:
        The API key string.
    name:
        Human-readable name for the key owner.
    roles:
        List of roles assigned to this key.

    Returns
    -------
    str
        The hashed key identifier.
    """
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    _VALID_API_KEYS[key_hash] = {
        "name": name,
        "roles": roles or ["reader"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("API key registered for %s", name)
    return key_hash


def generate_api_key(prefix: str = "gos") -> str:
    """Generate a new random API key.

    Returns
    -------
    str
        A securely generated API key string.
    """
    return f"{prefix}_{secrets.token_urlsafe(32)}"


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),  # noqa: B008
) -> dict[str, Any]:
    """FastAPI dependency to verify an API key.

    Raises
    ------
    HTTPException
        If the API key is missing or invalid.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_info = _VALID_API_KEYS.get(key_hash)

    if key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return key_info


# ── JWT Authentication ──────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)

# In production, use a proper secret from environment
_JWT_SECRET = secrets.token_urlsafe(64)
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24


def create_jwt_token(
    subject: str,
    roles: list[str] | None = None,
    expiry_hours: float = _JWT_EXPIRY_HOURS,
) -> str:
    """Create a JWT token.

    Parameters
    ----------
    subject:
        Token subject (e.g. user ID or service name).
    roles:
        Roles to embed in the token.
    expiry_hours:
        Token validity in hours.

    Returns
    -------
    str
        Encoded JWT token string.
    """
    try:
        import jwt
    except ImportError as err:
        logger.error("PyJWT not installed — cannot create JWT tokens")
        raise ImportError("PyJWT is required for JWT authentication") from err

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "roles": roles or ["reader"],
        "iat": now,
        "exp": now + timedelta(hours=expiry_hours),
    }
    encoded: str = jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
    return encoded


def verify_jwt_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT token.

    Parameters
    ----------
    token:
        The JWT token string.

    Returns
    -------
    dict
        Decoded token payload.

    Raises
    ------
    HTTPException
        If the token is invalid or expired.
    """
    try:
        import jwt
    except ImportError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT support not available",
        ) from err

    try:
        decoded: dict[str, Any] = jwt.decode(
            token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM]
        )
        return decoded
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from err
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),  # noqa: B008
) -> dict[str, Any]:
    """FastAPI dependency to verify a Bearer JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )
    return verify_jwt_token(credentials.credentials)


# ── Role Checking ───────────────────────────────────────────────────────────


def require_role(required_role: str):
    """Create a FastAPI dependency that checks for a specific role.

    Usage::

        @router.post("/admin/reset", dependencies=[Depends(require_role("admin"))])
        async def reset():
            ...
    """

    async def _check(
        auth_info: dict[str, Any] = Depends(verify_api_key),  # noqa: B008
    ) -> dict[str, Any]:
        roles = auth_info.get("roles", [])
        if required_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return auth_info

    return _check
