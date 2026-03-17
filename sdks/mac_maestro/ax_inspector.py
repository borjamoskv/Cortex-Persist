"""Mac-Maestro-Ω — Accessibility Inspector (Vector B)."""

from __future__ import annotations

import logging
from typing import Any

try:
    from ApplicationServices import (
        AXUIElementCopyAttributeValue,
        AXUIElementCreateApplication,
        AXUIElementCreateSystemWide,  # noqa: F401
        kAXChildrenAttribute,
        kAXDescriptionAttribute,
        kAXEnabledAttribute,
        kAXFocusedAttribute,
        kAXIdentifierAttribute,
        kAXPositionAttribute,
        kAXRoleAttribute,
        kAXSizeAttribute,
        kAXSubroleAttribute,
        kAXTitleAttribute,
        kAXValueAttribute,
    )

    AX_AVAILABLE = True
except ImportError:
    AX_AVAILABLE = False

from .models import AXNodeSnapshot

logger = logging.getLogger("mac_maestro.ax_inspector")


class AXInspectorError(Exception):
    pass


def check_ax_availability() -> None:
    if not AX_AVAILABLE:
        raise AXInspectorError("pyobjc-framework-ApplicationServices not available.")


def get_ax_attribute(element: Any, attribute: str) -> Any:
    """Safely retrieve an AX attribute."""
    err, val = AXUIElementCopyAttributeValue(element, attribute, None)
    return val if err == 0 else None


def _extract_point(ax_value: Any) -> tuple[float, float] | None:
    if ax_value is None:
        return None
    try:
        return (float(ax_value.x), float(ax_value.y))
    except (AttributeError, TypeError):
        return None


def _extract_size(ax_value: Any) -> tuple[float, float] | None:
    if ax_value is None:
        return None
    try:
        return (float(ax_value.width), float(ax_value.height))
    except (AttributeError, TypeError):
        return None


def build_snapshot(
    element: Any,
    path: tuple[int, ...] = (),
    depth: int = 0,
    max_depth: int = 15,
) -> AXNodeSnapshot:
    """Build a semantic snapshot of an accessibility tree."""
    check_ax_availability()

    if depth > max_depth:
        return AXNodeSnapshot(
            role="MAX_DEPTH_REACHED",
            subrole=None,
            title=None,
            value=None,
            identifier=None,
            description=None,
            enabled=None,
            focused=None,
            position=None,
            size=None,
            path=path,
            children=[],
        )

    role = get_ax_attribute(element, kAXRoleAttribute)
    subrole = get_ax_attribute(element, kAXSubroleAttribute)
    title = get_ax_attribute(element, kAXTitleAttribute)
    value = get_ax_attribute(element, kAXValueAttribute)
    identifier = get_ax_attribute(element, kAXIdentifierAttribute)
    description = get_ax_attribute(element, kAXDescriptionAttribute)
    enabled = get_ax_attribute(element, kAXEnabledAttribute)
    focused = get_ax_attribute(element, kAXFocusedAttribute)
    raw_pos = get_ax_attribute(element, kAXPositionAttribute)
    raw_size = get_ax_attribute(element, kAXSizeAttribute)

    snapshot = AXNodeSnapshot(
        role=role,
        subrole=subrole,
        title=title,
        value=str(value) if value is not None else None,
        identifier=identifier,
        description=description,
        enabled=bool(enabled) if enabled is not None else None,
        focused=bool(focused) if focused is not None else None,
        position=_extract_point(raw_pos),
        size=_extract_size(raw_size),
        path=path,
        children=[],
    )

    children_val = get_ax_attribute(element, kAXChildrenAttribute)
    if children_val:
        for i, child_elem in enumerate(children_val):
            snapshot.children.append(
                build_snapshot(
                    child_elem,
                    path + (i,),
                    depth + 1,
                    max_depth,
                )
            )
    return snapshot


def get_window_title(pid: int) -> str | None:
    """Extract the title of the first AXWindow of an application."""
    check_ax_availability()
    app_element = AXUIElementCreateApplication(pid)
    children = get_ax_attribute(app_element, kAXChildrenAttribute)
    if not children:
        return None
    for child in children:
        role = get_ax_attribute(child, kAXRoleAttribute)
        if role == "AXWindow":
            return get_ax_attribute(child, kAXTitleAttribute)
    return None


def inspect_app(pid: int) -> AXNodeSnapshot:
    """Create an AX snapshot for an application."""
    check_ax_availability()
    return build_snapshot(AXUIElementCreateApplication(pid))
