# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, Header, HTTPException, Request

from cortex.auth.manager import get_auth_manager
from cortex.auth.models import AuthResult
from cortex.auth.rbac import RBAC, Permission

__all__ = [
    "require_auth",
    "require_consensus",
    "require_permission",
    "require_verified_permission",
]

logger = logging.getLogger(__name__)


async def require_auth(
    request: Request,
    authorization: str | None = Header(
        None,
        description="Bearer <api-key>",
    ),
) -> AuthResult:
    """Extract and validate API key from Authorization header."""
    from cortex.utils.i18n import get_trans

    lang = request.headers.get("Accept-Language", "en")

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail=get_trans("error_missing_auth", lang),
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail=get_trans("error_invalid_key_format", lang),
        )

    manager = get_auth_manager()
    result = await manager.authenticate_async(parts[1])
    if not result.authenticated:
        error_msg = get_trans("error_invalid_revoked_key", lang) if result.error else result.error
        raise HTTPException(status_code=401, detail=error_msg)

    # SECURE LINK: Bind the dynamic tenant context to the authenticated identity
    from cortex.extensions.security.tenant import tenant_id_var

    tenant_id_var.set(result.tenant_id)

    return result


def require_permission(permission: str | Permission):
    """Factory for permission-checking dependencies.

    Supports both legacy string permissions and CORTEX v6 Permission enums.
    """

    async def checker(
        request: Request,
        auth: AuthResult = Depends(require_auth),
    ) -> AuthResult:
        has_perm = False
        if isinstance(permission, str) and permission in auth.permissions:
            has_perm = True
        elif isinstance(permission, Permission):
            has_perm = RBAC.has_permission(auth.role, permission)

        if not has_perm and str(permission) in auth.permissions:
            has_perm = True

        if not has_perm:
            from cortex.utils.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            perm_name = permission.name if isinstance(permission, Permission) else permission
            detail = get_trans(
                "error_missing_permission",
                lang,
            ).format(permission=perm_name)
            raise HTTPException(status_code=403, detail=detail)
        return auth

    return checker


async def require_consensus(
    claim: str,
    min_score: float = 1.6,
    engine: Any = Depends(lambda: None),
) -> bool:
    """Verify a claim has reached sufficient consensus with KV-Aware Caching (Ω₂)."""
    from cortex.auth.cache import AUTH_CACHE
    from cortex.extensions.security.tenant import get_tenant_id

    tenant_id = get_tenant_id()
    cached_score = AUTH_CACHE.get(claim, tenant_id)
    if cached_score is not None:
        return cached_score >= min_score

    if engine is None:
        from cortex.api.deps import get_async_engine

        async for e in get_async_engine():  # type: ignore[reportCallIssue]
            engine = e
            break

    results = await engine.search(query=claim, top_k=1)  # pyright: ignore[reportOptionalMemberAccess]
    if not results:
        return False

    res = results[0]
    score = (
        res.meta.get("consensus_score", 0.0)
        if hasattr(res, "meta")
        else res.get("consensus_score", 0.0)
    )

    # Store in cache for future high-speed retrieval
    AUTH_CACHE.set(claim, tenant_id, score)

    if score < min_score:
        logger.warning(
            "[AUTH] Consensus too low: %.2f < %.2f for claim: '%s'",
            score,
            min_score,
            claim,
        )
        return False
    return True


def require_verified_permission(
    permission: str,
    min_consensus: float = 1.6,
):
    """Sovereign Gate: Requires both permission AND verified claim."""

    async def sovereign_checker(
        request: Request,
        auth: AuthResult = Depends(require_auth),
    ) -> AuthResult:
        if permission not in auth.permissions:
            from cortex.utils.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            detail = get_trans(
                "error_missing_permission",
                lang,
            ).format(permission=permission)
            raise HTTPException(status_code=403, detail=detail)

        from cortex.api.deps import get_async_engine

        engine = None
        async for e in get_async_engine():  # type: ignore[reportCallIssue]
            engine = e
            break

        if engine:
            has_consensus = await require_consensus(
                f"Permission {permission} granted to {auth.key_name or auth.tenant_id}",
                min_score=min_consensus,
                engine=engine,
            )
            if not has_consensus:
                detail = f"Sovereign Gate: Action requires consensus (min: {min_consensus})"
                raise HTTPException(status_code=403, detail=detail)

        return auth

    return sovereign_checker
