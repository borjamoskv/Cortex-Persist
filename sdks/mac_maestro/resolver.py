"""Mac-Maestro-Ω — Vector Resolution Engine (V5).

Maps action.vector strings (A/B/C/D) to concrete executor callables.
Supports ResolvedTarget from the Element Resolution Pipeline.
"""

from __future__ import annotations

import functools
import logging
from typing import Any

from .models import ActionFailed, ResolvedTarget, UIAction

logger = logging.getLogger("mac_maestro.resolver")


def resolve(
    action: UIAction,
    resolved_target: ResolvedTarget | None = None,
) -> Any:
    """Resolve an action's vector to a concrete executor callable.

    If a ResolvedTarget is provided (from the Element Resolution Pipeline),
    it enriches the resolution with real PID, element ref, and coordinates.

    Args:
        action: The UIAction to resolve.
        resolved_target: Optional pre-resolved target from the matcher.

    Returns:
        A zero-argument callable that performs the action.

    Raises:
        ActionFailed: If the vector is unknown or resolution fails.
    """
    registry: dict[str, Any] = {
        "A": _resolve_applescript,
        "B": _resolve_ax,
        "C": _resolve_keyboard,
        "D": _resolve_cgevent,
    }

    resolver_fn = registry.get(action.vector)
    if resolver_fn is None:
        raise ActionFailed(
            f"Unknown vector '{action.vector}' for action '{action.name}'. "
            f"Valid: {sorted(registry.keys())}"
        )

    return resolver_fn(action, resolved_target)


# ═══════════════════════════════════════════════════════════════════
# Vector A: AppleScript
# ═══════════════════════════════════════════════════════════════════


def _resolve_applescript(
    action: UIAction,
    resolved_target: ResolvedTarget | None,
) -> Any:
    """Build an AppleScript executor from target_query."""
    from .applescript import activate_app_by_name, open_url_in_safari, run_applescript

    q = action.target_query

    if "script" in q:
        return functools.partial(run_applescript, q["script"])
    if "app_name" in q:
        return functools.partial(activate_app_by_name, q["app_name"])
    if "url" in q:
        return functools.partial(open_url_in_safari, q["url"])

    raise ActionFailed(
        f"Vector A (AppleScript) requires 'script', 'app_name', or 'url' "
        f"in target_query. Got: {sorted(q.keys())}"
    )


# ═══════════════════════════════════════════════════════════════════
# Vector B: AXUIElement
# ═══════════════════════════════════════════════════════════════════


def _resolve_ax(
    action: UIAction,
    resolved_target: ResolvedTarget | None,
) -> Any:
    """Build an AX action executor.

    If a ResolvedTarget with an element ref is available, uses it directly.
    Otherwise falls back to target_query keys (pid, element_path, action_name).
    """
    try:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            AXUIElementPerformAction,
            kAXChildrenAttribute,
        )
    except ImportError as exc:
        raise ActionFailed(
            "Vector B (AXUIElement) requires pyobjc-framework-ApplicationServices."
        ) from exc

    q = action.target_query
    ax_action = q.get("action_name", "AXPress")

    # ── If resolved target has a live element ref, use it directly ──
    if resolved_target and resolved_target.element and resolved_target.element.ref:
        element_ref = resolved_target.element.ref

        def _press_resolved():
            err = AXUIElementPerformAction(element_ref, ax_action)
            if err != 0:
                raise ActionFailed(
                    f"AXPerformAction({ax_action}) failed with error {err} on resolved element"
                )

        return _press_resolved

    # ── Fallback: manual PID + element_path resolution ──
    pid = q.get("pid") or (resolved_target.pid if resolved_target else None)
    element_path = q.get("element_path")

    if pid is None:
        raise ActionFailed("Vector B requires 'pid' in target_query or a resolved target.")
    if element_path is None:
        raise ActionFailed("Vector B requires 'element_path' in target_query.")

    def _ax_execute():
        app = AXUIElementCreateApplication(pid)
        element = app
        for idx in element_path:
            err, children = AXUIElementCopyAttributeValue(
                element,
                kAXChildrenAttribute,
                None,
            )
            if err != 0 or not children or idx >= len(children):
                raise ActionFailed(f"AX tree traversal failed at index {idx}")
            element = children[idx]
        err = AXUIElementPerformAction(element, ax_action)
        if err != 0:
            raise ActionFailed(f"AXPerformAction({ax_action}) error {err}")

    return _ax_execute


# ═══════════════════════════════════════════════════════════════════
# Vector C: Keyboard
# ═══════════════════════════════════════════════════════════════════


def _resolve_keyboard(
    action: UIAction,
    resolved_target: ResolvedTarget | None,
) -> Any:
    """Build a keyboard executor from target_query."""
    try:
        from .keyboard import press_key, type_text
    except ImportError as exc:
        raise ActionFailed("Vector C (Keyboard) module not available.") from exc

    q = action.target_query

    if "text" in q:
        method = q.get("method", "cgevent")
        return functools.partial(type_text, q["text"], method=method)
    if "keycode" in q:
        return functools.partial(press_key, q["keycode"])

    raise ActionFailed(
        f"Vector C (Keyboard) requires 'text' or 'keycode' in target_query. Got: {sorted(q.keys())}"
    )


# ═══════════════════════════════════════════════════════════════════
# Vector D: CGEvent
# ═══════════════════════════════════════════════════════════════════


def _resolve_cgevent(
    action: UIAction,
    resolved_target: ResolvedTarget | None,
) -> Any:
    """Build a CGEvent executor.

    If a ResolvedTarget with position is available, uses its click-center
    coordinates automatically. Otherwise requires (x, y) in target_query.
    """
    try:
        from .cgevents import click_at, drag_to
    except ImportError as exc:
        raise ActionFailed("Vector D (CGEvent) module not available.") from exc

    q = action.target_query

    # ── Auto-extract coordinates from resolved element ──
    x = q.get("x")
    y = q.get("y")

    if x is None and y is None and resolved_target and resolved_target.position:
        x, y = resolved_target.position
        logger.info(
            "Vector D: auto-extracted coordinates (%.1f, %.1f) from resolved element",
            x,
            y,
        )

    if "drag_to_x" in q and "drag_to_y" in q:
        if x is None or y is None:
            raise ActionFailed("Vector D (drag) requires start coordinates (x, y).")
        return functools.partial(
            drag_to,
            float(x),
            float(y),
            float(q["drag_to_x"]),
            float(q["drag_to_y"]),
        )

    if x is not None and y is not None:
        return functools.partial(click_at, float(x), float(y))

    raise ActionFailed(
        f"Vector D (CGEvent) requires (x, y) in target_query or a "
        f"resolved element with position. Got: {sorted(q.keys())}"
    )
