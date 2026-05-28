"""Guard Pipeline — Composable pre-store, mutate, and post-store chain.

Replaces the hardcoded try/except ImportError blocks in store_mixin._store_impl
with a registered list of protocol-conforming guards, mutators, and hooks.

Guard failures follow the active profile: dev warns and continues for optional
surfaces; compliance fails closed.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import aiosqlite

from cortex.extensions.interfaces.store_pipeline import ContentMutator, PostStoreHook, StoreGuard

__all__ = ["GuardPipeline", "guard_profile_fail_closed", "resolve_guard_profile"]

logger = logging.getLogger("cortex.engine")

GUARD_PROFILE_ENV = "CORTEX_GUARD_PROFILE"
STRICT_GUARDS_ENV = "CORTEX_STRICT_GUARDS"
DEV_GUARD_PROFILES = {"dev", "development", "local"}
COMPLIANCE_GUARD_PROFILES = {"compliance", "prod", "production", "strict"}
POST_HOOK_FAILURES = (
    AttributeError,
    ImportError,
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
    aiosqlite.Error,
)


def resolve_guard_profile(profile: str | None = None) -> str:
    """Resolve the guard profile from explicit config or environment."""
    raw_profile = profile or os.getenv(GUARD_PROFILE_ENV)
    if raw_profile is None and os.getenv(STRICT_GUARDS_ENV) == "1":
        raw_profile = "compliance"

    normalized = (raw_profile or "dev").strip().lower()
    if normalized in DEV_GUARD_PROFILES:
        return "dev"
    if normalized in COMPLIANCE_GUARD_PROFILES:
        return "compliance"
    raise ValueError(f"Unknown guard profile: {raw_profile}")


def guard_profile_fail_closed(profile: str | None = None) -> bool:
    """Return True when the resolved guard profile must fail closed."""
    return resolve_guard_profile(profile) == "compliance"


class GuardPipeline:
    """Orchestrates pre-store guards, content mutators, and post-store hooks."""

    def __init__(self, profile: str | None = None) -> None:
        self.profile = resolve_guard_profile(profile)
        self.fail_closed = guard_profile_fail_closed(self.profile)
        self._guards: list[StoreGuard] = []
        self._mutators: list[ContentMutator] = []
        self._post_hooks: list[PostStoreHook] = []

    # ─── Registration ─────────────────────────────────────────────

    def add_guard(self, guard: StoreGuard) -> None:
        self._guards.append(guard)

    def add_mutator(self, mutator: ContentMutator) -> None:
        self._mutators.append(mutator)

    def add_post_hook(self, hook: PostStoreHook) -> None:
        self._post_hooks.append(hook)

    # ─── Execution ────────────────────────────────────────────────

    async def run_guards(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Run all pre-store guards. First rejection raises ValueError."""
        for guard in self._guards:
            await guard.check(content, project, fact_type, meta, conn, tenant_id=tenant_id)

    async def run_mutators(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Run all content mutators in order. Each receives the previous output."""
        for mutator in self._mutators:
            content, fact_type, meta = await mutator.transform(
                content,
                project,
                fact_type,
                meta,
                conn,
                tenant_id=tenant_id,
                source=source,
            )
        return content, fact_type, meta

    async def run_post_hooks(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        """Run all post-store hooks according to the active guard profile."""
        for hook in self._post_hooks:
            try:
                await hook.on_stored(
                    fact_id,
                    project,
                    fact_type,
                    conn,
                    tenant_id=tenant_id,
                    source=source,
                    db_path=db_path,
                )
            except POST_HOOK_FAILURES as e:
                if self.fail_closed:
                    raise RuntimeError(
                        f"FAIL-CLOSED: post-store hook {type(hook).__name__} failed: {e}"
                    ) from e
                logger.warning(
                    "[GuardPipeline] Post-hook %s failed: %s",
                    type(hook).__name__,
                    e,
                )

    @property
    def guard_count(self) -> int:
        return len(self._guards)

    @property
    def mutator_count(self) -> int:
        return len(self._mutators)

    @property
    def hook_count(self) -> int:
        return len(self._post_hooks)
