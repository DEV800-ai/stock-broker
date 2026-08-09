"""Shared-secret auth for single-operator deployment.

Every route except /health requires X-API-Key to match settings.api_key.
X-Actor optionally identifies who is acting, so audit/approval records stop
defaulting to a hardcoded "human"/"system" string.
"""
import hmac

from fastapi import Header, HTTPException, status

from broker.config import settings

DEFAULT_ACTOR = "operator"


def require_actor(
    x_api_key: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
) -> str:
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is misconfigured: API_KEY is not set",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
    actor = (x_actor or "").strip()
    return actor or DEFAULT_ACTOR
