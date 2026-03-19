"""Mac-Maestro-Ω — Central workflow orchestrator with full Master Protocol.

Supports both synchronous and async execution.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid

from .models import ActionFailed, ResolvedTarget, UIAction
from .trace import emit_trace

logger = logging.getLogger("mac_maestro.workflow")

# ─── Safety Gates ──────────────────────────────────────────────────

SAFE_ACTIONS = frozenset(
    {
        "inspect",
        "focus",
        "read",
        "open",
        "copy",
        "activate",
        "hide",
    }
)

UNSAFE_ACTIONS = frozenset(
    {
        "delete",
        "send",
        "overwrite",
        "move",
        "close_without_save",
        "replace",
        "submit",
        "bulk_type",
        "drag_drop_cross_app",
    }
)

# ─── Backoff Constants ─────────────────────────────────────────────

BACKOFF_BASE: float = 0.1
BACKOFF_CAP: float = 5.0
BACKOFF_JITTER: float = 0.1

# ─── Semantic query keys ───────────────────────────────────────────

_SEMANTIC_KEYS = frozenset({"role", "title", "description", "identifier", "value"})


def _backoff_sleep(attempt: int) -> float:
    """Exponential backoff with jitter (synchronous)."""
    delay = min(BACKOFF_BASE * (2**attempt), BACKOFF_CAP)
    jitter = random.uniform(0, BACKOFF_JITTER)  # noqa: S311
    total = delay + jitter
    time.sleep(total)
    return total


async def _async_backoff_sleep(attempt: int) -> float:
    """Exponential backoff with jitter (async)."""
    delay = min(BACKOFF_BASE * (2**attempt), BACKOFF_CAP)
    jitter = random.uniform(0, BACKOFF_JITTER)  # noqa: S311
    total = delay + jitter
    await asyncio.sleep(total)
    return total


def require_safety_gate(action: UIAction) -> None:
    """Enforce that unsafe actions are explicitly cleared."""
    if action.unsafe or action.name in UNSAFE_ACTIONS:
        raise PermissionError(
            f"[SAFETY GATE] Action '{action.name}' (vector={action.vector}) "
            f"requires explicit bypass."
        )


class MacMaestroWorkflow:
    """Central orchestrator for Sovereign Mac Automation.

    Master Protocol (all 5 phases implemented):
    1. Target Lock   → Resolve bundle_id to PID, activate app
    2. State Verify  → Confirm frontmost, capture window_title
    3. Element Resolve → Semantic search over AX tree → ElementMatch
    4. Action Execute → Execute with Action Ladder fallback
    5. Postcondition Verify → Check postconditions, retry if idempotent
    """

    def __init__(self, bundle_id: str) -> None:
        self.bundle_id = bundle_id
        self.run_id = f"mac-omega-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        self.current_app_pid: int | None = None
        self.is_frontmost: bool = False
        self.window_title: str | None = None
        self._resolved: ResolvedTarget | None = None

    def _target_lock(self) -> None:
        """Phase 1 + 2: Target Lock and State Verify.

        Resolves bundle_id to PID, checks frontmost status,
        extracts window title. Degrades gracefully if AppKit unavailable.
        """
        try:
            from .app_discovery import (
                get_pid,
                is_frontmost,
            )
            from .ax_inspector import get_window_title

            self.current_app_pid = get_pid(self.bundle_id)
            self.is_frontmost = is_frontmost(self.bundle_id)
            self.window_title = get_window_title(self.current_app_pid)
            logger.info(
                "Target Lock: %s (pid=%d, frontmost=%s, window=%s)",
                self.bundle_id,
                self.current_app_pid,
                self.is_frontmost,
                self.window_title,
            )
        except ActionFailed:
            raise
        except Exception as e:
            logger.warning("Target Lock degraded: %s", e)
            self._resolved = ResolvedTarget(
                pid=0,
                app_name="unknown",
                bundle_id=self.bundle_id,
                window_title=None,
                element=None,
                position=None,
                resolution_method="degraded",
                degraded=True,
            )

    def _element_resolve(self, action: UIAction) -> ResolvedTarget | None:
        """Phase 3: Semantic element resolution.

        If target_query contains semantic keys (role, title, etc.),
        builds an AX snapshot and runs the matcher.
        """
        query_keys = set(action.target_query.keys())
        if not query_keys & _SEMANTIC_KEYS:
            return None

        if self.current_app_pid is None:
            logger.warning("Element resolve skipped: no PID (Target Lock failed)")
            return None

        try:
            from .ax_inspector import inspect_app
            from .matcher import find_best

            snapshot = inspect_app(self.current_app_pid)
            match = find_best(
                snapshot,
                role=action.target_query.get("role"),
                title=action.target_query.get("title"),
                description=action.target_query.get("description"),
                identifier=action.target_query.get("identifier"),
                value=action.target_query.get("value"),
            )

            try:
                from .app_discovery import get_app_name

                app_name = get_app_name(self.bundle_id)
            except Exception:
                app_name = self.bundle_id

            if match is not None:
                resolved = ResolvedTarget(
                    pid=self.current_app_pid,
                    app_name=app_name,
                    bundle_id=self.bundle_id,
                    window_title=self.window_title,
                    element=match,
                    position=match.center,
                    resolution_method="ax_semantic",
                    degraded=False,
                    candidates_count=1,
                    confidence=match.score,
                )
                logger.info(
                    "Element resolved: %s (score=%.2f, reasons=%s)",
                    match.role,
                    match.score,
                    match.reasons,
                )
                self._resolved = resolved
                return resolved

            logger.warning(
                "No element matched query %s in AX tree",
                {k: v for k, v in action.target_query.items() if k in _SEMANTIC_KEYS},
            )
            return None

        except Exception as e:
            logger.warning("Element resolve failed: %s", e)
            return None

    def execute_action(
        self,
        action: UIAction,
        apply_safety_gate: bool = True,
    ) -> bool:
        """Execute a UIAction following the full Master Protocol.

        Phases: Target Lock → State Verify → Element Resolve →
                Action Execute → Postcondition Verify.

        If the primary action fails, automatically attempts fallback actions
        in sequence (True Action Ladder: B → D → C → A).
        """
        # ── Phase 1+2: Target Lock + State Verify ──
        self._target_lock()

        actions_to_try = [action, *action.fallbacks]
        last_error: ActionFailed | None = None

        for idx, current_action in enumerate(actions_to_try):
            try:
                if idx > 0:
                    logger.warning(
                        "Attempting fallback %d: %s (Vector %s)",
                        idx,
                        current_action.name,
                        current_action.vector,
                    )
                self._execute_single_action(current_action, apply_safety_gate)
                return True
            except ActionFailed as e:
                last_error = e
                logger.warning(
                    "Action %s (Vector %s) failed: %s",
                    current_action.name,
                    current_action.vector,
                    e,
                )

        raise ActionFailed(
            f"All fallback vectors exhausted for {action.name}. Last error: {last_error}"
        )

    def run_sequence(
        self,
        actions: list[UIAction],
        apply_safety_gate: bool = True,
        abort_on_failure: bool = True,
    ) -> list[bool]:
        """Execute a sequence of UIActions with shared workflow state."""
        results: list[bool] = []
        for i, action in enumerate(actions):
            try:
                result = self.execute_action(action, apply_safety_gate)
                results.append(result)
            except (ActionFailed, PermissionError) as e:
                logger.error(
                    "Sequence step %d (%s) failed: %s",
                    i,
                    action.name,
                    e,
                )
                if abort_on_failure:
                    raise
                results.append(False)
        return results

    async def execute_action_async(
        self,
        action: UIAction,
        apply_safety_gate: bool = True,
    ) -> bool:
        """Async variant of execute_action.

        Wraps synchronous execution in asyncio.to_thread() to avoid
        blocking the event loop.
        """
        return await asyncio.to_thread(
            self.execute_action,
            action,
            apply_safety_gate,
        )

    async def run_sequence_async(
        self,
        actions: list[UIAction],
        apply_safety_gate: bool = True,
        abort_on_failure: bool = True,
    ) -> list[bool]:
        """Async variant of run_sequence."""
        return await asyncio.to_thread(
            self.run_sequence,
            actions,
            apply_safety_gate,
            abort_on_failure,
        )

    def _execute_single_action(
        self,
        action: UIAction,
        apply_safety_gate: bool,
    ) -> None:
        """Execute a single UIAction attempt."""
        logger.info(
            "Executing: %s (Vector %s)",
            action.name,
            action.vector,
        )

        if apply_safety_gate:
            require_safety_gate(action)

        # ── Preconditions ──
        pre_results: dict[str, bool] = {}
        for i, check in enumerate(action.preconditions):
            res = check()
            pre_results[f"pre_{i}"] = res
            if not res:
                self._trace(action, "failure", pre_results, {}, "precondition_failed")
                raise ActionFailed(f"Precondition {i} failed for {action.name}")

        # ── Phase 3: Element Resolve ──
        resolved = self._element_resolve(action)

        # ── Auto-resolve executor if not provided ──
        executor = action.executor
        if executor is None:
            from .resolver import resolve

            executor = resolve(action, resolved_target=resolved)

        # ── Phase 4+5: Execute + Retry (Exponential Backoff) ──
        attempts = 0
        success = False
        limit = action.retry_limit if action.idempotent else 1

        while attempts < limit and not success:
            attempts += 1
            try:
                executor()

                post_results: dict[str, bool] = {}
                all_post_passed = True
                for j, check in enumerate(action.postconditions):
                    res = check()
                    post_results[f"post_{j}"] = res
                    if not res:
                        all_post_passed = False

                if all_post_passed:
                    success = True
                    self._trace(
                        action,
                        "success",
                        pre_results,
                        post_results,
                        click_target=resolved.position if resolved else None,
                    )
                else:
                    self._trace(
                        action,
                        "failure",
                        pre_results,
                        post_results,
                        "postcondition_failed",
                        retry=attempts,
                        click_target=resolved.position if resolved else None,
                    )
                    if not action.idempotent:
                        raise ActionFailed(
                            f"Postconditions failed on non-idempotent "
                            f"action {action.name}. Aborting."
                        )

            except ActionFailed:
                raise
            except Exception as e:
                self._trace(
                    action,
                    "error",
                    pre_results,
                    {},
                    failure_class=str(e),
                    retry=attempts,
                )
                if not action.idempotent:
                    raise ActionFailed(f"Executor crashed on non-idempotent action: {e}") from e
                _backoff_sleep(attempts)

        if not success:
            raise ActionFailed(f"Action {action.name} exhausted {limit} retries.")

    def _trace(
        self,
        action: UIAction,
        outcome: str,
        pre_res: dict[str, bool],
        post_res: dict[str, bool],
        failure_class: str | None = None,
        retry: int = 0,
        click_target: tuple[float, float] | None = None,
    ) -> None:
        """Emit a structured trace with real context from Target Lock."""
        resolved = self._resolved
        emit_trace(
            run_id=self.run_id,
            bundle_id=self.bundle_id,
            pid=self.current_app_pid,
            frontmost=self.is_frontmost,
            window_title=self.window_title,
            selected_vector=action.vector,
            outcome=outcome,
            target_query=action.target_query,
            matched_element=(
                {
                    "role": resolved.element.role,
                    "title": resolved.element.title,
                    "score": resolved.element.score,
                    "reasons": resolved.element.reasons,
                    "position": resolved.element.position,
                }
                if resolved and resolved.element
                else None
            ),
            precondition_results=pre_res,
            postcondition_results=post_res,
            retry_count=retry,
            failure_class=failure_class,
            resolution_method=(resolved.resolution_method if resolved else None),
            resolution_confidence=(resolved.confidence if resolved else None),
            candidates_count=(resolved.candidates_count if resolved else 0),
            click_target=click_target,
        )
