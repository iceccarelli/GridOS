"""Optional authentication helpers for GridOS.

Authentication is not enforced by default in the reduced launch version. This
module provides a small, honest foundation that can be used when an operator
explicitly enables API-key or JWT-based access in a local deployment.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from gridos.config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)
_VALID_API_KEYS: dict[str, dict[str, Any]] = {}
_JWT_ALGORITHM = "HS256"


def auth_enabled() -> bool:
    """Return whether auth is explicitly enabled for the current process."""
    return bool(settings.secret_key and settings.secret_key != "change-me-to-a-random-string")


def register_api_key(key: str, name: str, roles: list[str] | None = None) -> str:
    """Register an API key in the in-memory key registry."""
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    _VALID_API_KEYS[key_hash] = {
        "name": name,
        "roles": roles or ["operator"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("API key registered for %s", name)
    return key_hash


def generate_api_key(prefix: str = "gos") -> str:
    """Generate a random API key suitable for local use."""
    return f"{prefix}_{secrets.token_urlsafe(32)}"


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),  # noqa: B008
) -> dict[str, Any]:
    """Verify an API key when auth has been explicitly enabled."""
    if not auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not enabled in this GridOS deployment.",
        )

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required.",
        )

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_info = _VALID_API_KEYS.get(key_hash)
    if key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    return key_info


def create_jwt_token(
    subject: str,
    roles: list[str] | None = None,
    expiry_hours: float = 24,
) -> str:
    """Create a JWT token using the configured GridOS secret key."""
    if not auth_enabled():
        raise RuntimeError("Authentication is not enabled in this GridOS deployment.")

    try:
        import jwt
    except ImportError as err:
        raise RuntimeError("PyJWT is required for JWT support.") from err

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "roles": roles or ["operator"],
        "iat": now,
        "exp": now + timedelta(hours=expiry_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT token when auth is enabled."""
    if not auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not enabled in this GridOS deployment.",
        )

    try:
        import jwt
    except ImportError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT support is not available.",
        ) from err

    try:
        decoded: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_JWT_ALGORITHM],
        )
        return decoded
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        ) from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        ) from err


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),  # noqa: B008
) -> dict[str, Any]:
    """Verify a bearer token when auth is enabled."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
        )
    return verify_jwt_token(credentials.credentials)


def require_role(required_role: str):
    """Return a dependency that checks for one required role.

    Role checks accept either a valid API key or a valid bearer token once auth
    has been explicitly enabled.
    """

    async def _check(
        api_key_info: dict[str, Any] | None = Security(_api_key_header),  # type: ignore[assignment]  # noqa: B008
        bearer: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),  # noqa: B008
    ) -> dict[str, Any]:
        if not auth_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not enabled in this GridOS deployment.",
            )

        auth_info: dict[str, Any] | None = None
        if api_key_info:
            key_hash = hashlib.sha256(api_key_info.encode()).hexdigest()
            auth_info = _VALID_API_KEYS.get(key_hash)
        elif bearer:
            auth_info = verify_jwt_token(bearer.credentials)

        if auth_info is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid credentials required.",
            )

        roles = auth_info.get("roles", [])
        if required_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required.",
            )
        return auth_info

    return _check
