"""Shared-secret auth for single-operator deployment.

Every route except /health requires X-API-Key to match settings.api_key.
X-Actor optionally identifies who is acting, so audit/approval records stop
defaulting to a hardcoded "human"/"system" string.

require_human_actor additionally requires X-Human-Key to match
settings.human_approval_key, on endpoints that must only ever be triggered by
a human (order/paper-trade approval, kill switch) — see its docstring.
"""
import hmac

from fastapi import Header, HTTPException, status

from broker.config import settings

DEFAULT_ACTOR = "operator"


def _check_api_key(x_api_key: str | None) -> None:
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


def require_actor(
    x_api_key: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
) -> str:
    _check_api_key(x_api_key)
    actor = (x_actor or "").strip()
    return actor or DEFAULT_ACTOR


def require_human_actor(
    x_api_key: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
    x_human_key: str | None = Header(default=None),
) -> str:
    """Like require_actor, but also requires X-Human-Key when settings.human_approval_key
    is configured. Apply this (not require_actor) to any endpoint that must only ever be
    triggered by a human — order/paper-trade approval, agent kill switch, autonomy mode.
    If human_approval_key is unset (the default), this behaves exactly like require_actor,
    so existing single-key deployments are unaffected until an operator opts in by setting
    HUMAN_APPROVAL_KEY to something other than api_key.
    """
    _check_api_key(x_api_key)
    if settings.human_approval_key:
        if not x_human_key or not hmac.compare_digest(x_human_key, settings.human_approval_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid human confirmation key",
            )
    actor = (x_actor or "").strip()
    return actor or DEFAULT_ACTOR
