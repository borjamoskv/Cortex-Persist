from __future__ import annotations
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Optional

try:
    import ApplicationServices
    from AppKit import NSWorkspace
except ImportError:
    ApplicationServices = None
    NSWorkspace = None

from cortex.extensions.ui_control.models import AXElement, InteractionResult

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.extensions.ui_control.accessibility")

# Default max depth for tree traversals
DEFAULT_MAX_DEPTH = 8


class AccessibilityEngine:
    """
    Direct bridge to macOS Accessibility APIs using PyObjC.
    Handles element inspection, search, and interactions at the OS level.
    """

    def __init__(self, engine: Optional["CortexEngine"] = None) -> None:
        self.engine = engine

    def check_permissions(self) -> bool:
        """Verifies if the process has Accessibility permissions."""
        if not ApplicationServices:
            return False
        return ApplicationServices.AXIsProcessTrusted()

    def _get_app_element(self, app_name: str) -> Any:
        """Returns the base AXUIElement for a running application."""
        if not NSWorkspace:
            return None

        running_apps = NSWorkspace.sharedWorkspace().runningApplications()
        for app in running_apps:
            if app.localizedName() == app_name:
                return ApplicationServices.AXUIElementCreateApplication(app.processIdentifier())
        return None

    def _get_attribute(self, element: Any, attribute: str) -> Any:
        """Helper to safely retrieve an AX attribute."""
        error, value = ApplicationServices.AXUIElementCopyAttributeValue(element, attribute, None)
        if error == 0:
            return value
        return None

    # ─── Find by Identifier ─────────────────────────────────────

    def find_element(self, app_name: str, identifier: str) -> AXElement | None:
        """
        Recursively searches for an element with a specific AXIdentifier.
        This is the preferred method — language-independent.
        """
        app_ref = self._get_app_element(app_name)
        if not app_ref:
            return None
        return self._search_by_attribute(app_ref, "AXIdentifier", identifier)

    # ─── Find by Title ──────────────────────────────────────────

    def find_element_by_title(
        self,
        app_name: str,
        title: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> AXElement | None:
        """
        Searches for an element by AXTitle.
        Falls back to AXDescription for untitled elements.
        """
        app_ref = self._get_app_element(app_name)
        if not app_ref:
            return None

        result = self._search_by_attribute(app_ref, "AXTitle", title, max_depth)
        if result:
            return result
        # Fallback: AXDescription
        return self._search_by_attribute(app_ref, "AXDescription", title, max_depth)

    # ─── Find by Role ───────────────────────────────────────────

    def find_elements_by_role(
        self,
        app_name: str,
        role: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> list[AXElement]:
        """
        Returns all elements matching a specific AXRole (e.g., "AXButton", "AXTextField").
        """
        app_ref = self._get_app_element(app_name)
        if not app_ref:
            return []

        results: list[AXElement] = []
        self._collect_by_role(app_ref, role, results, 0, max_depth)
        return results

    def _collect_by_role(
        self,
        element: Any,
        target_role: str,
        results: list[AXElement],
        depth: int,
        max_depth: int,
    ) -> None:
        """Recursive collector for elements matching a given role."""
        current_role = self._get_attribute(element, "AXRole")
        if current_role and str(current_role) == target_role:
            results.append(self._build_model(element, depth))

        if depth >= max_depth:
            return

        children = self._get_attribute(element, "AXChildren")
        if children:
            for child in children:
                self._collect_by_role(child, target_role, results, depth + 1, max_depth)

    # ─── Tree Dump ──────────────────────────────────────────────

    def dump_tree(
        self,
        app_name: str,
        max_depth: int = 5,
    ) -> list[AXElement]:
        """
        Dumps the entire AX element tree for an application.
        Equivalent to Accessibility Inspector but in code.
        """
        app_ref = self._get_app_element(app_name)
        if not app_ref:
            return []

        elements: list[AXElement] = []
        self._traverse_tree(app_ref, elements, 0, max_depth)
        return elements

    def _traverse_tree(
        self,
        element: Any,
        elements: list[AXElement],
        depth: int,
        max_depth: int,
    ) -> None:
        """Recursive tree traversal, building flat list with depth info."""
        model = self._build_model(element, depth)
        elements.append(model)

        if depth >= max_depth:
            return

        children = self._get_attribute(element, "AXChildren")
        if children:
            for child in children:
                self._traverse_tree(child, elements, depth + 1, max_depth)

    # ─── Value Operations ───────────────────────────────────────

    def get_value(self, element: AXElement) -> str | None:
        """Reads AXValue from an element (text fields, sliders, etc)."""
        if not element.native_ref:
            return None
        val = self._get_attribute(element.native_ref, "AXValue")
        return str(val) if val is not None else None

    def set_value(self, element: AXElement, value: str) -> InteractionResult:
        """Writes AXValue to an element (text fields)."""
        if not element.native_ref or not ApplicationServices:
            return InteractionResult(success=False, error="No native reference or API")

        error = ApplicationServices.AXUIElementSetAttributeValue(
            element.native_ref, "AXValue", value
        )
        if error == 0:
            return InteractionResult(success=True)
        return InteractionResult(success=False, error=f"AXError setting value: {error}")

    # ─── Wait for Element ───────────────────────────────────────

    async def wait_for_element(
        self,
        app_name: str,
        identifier: str,
        timeout: float = 5.0,
        poll_interval: float = 0.25,
    ) -> AXElement | None:
        """
        Polls for an element until found or timeout.
        Returns the element if found, None if timed out.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            element = self.find_element(app_name, identifier)
            if element:
                return element
            await asyncio.sleep(poll_interval)
        return None

    # ─── Actions ────────────────────────────────────────────────

    async def perform_click(self, element: AXElement) -> InteractionResult:
        """Performs a default action (click) on the element."""
        if not element.native_ref or not ApplicationServices:
            return InteractionResult(success=False, error="No native reference found")

        error = ApplicationServices.AXUIElementPerformAction(element.native_ref, "AXPress")
        if error == 0:
            return InteractionResult(success=True)
        return InteractionResult(success=False, error=f"AXError: {error}")

    # ─── Internal Helpers ───────────────────────────────────────

    def _search_by_attribute(
        self,
        element: Any,
        attr_name: str,
        target_value: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
        depth: int = 0,
    ) -> AXElement | None:
        """Generic recursive search by any AX attribute value."""
        val = self._get_attribute(element, attr_name)
        if val is not None and str(val) == target_value:
            return self._build_model(element, depth)

        if depth >= max_depth:
            return None

        children = self._get_attribute(element, "AXChildren")
        if children:
            for child in children:
                found = self._search_by_attribute(
                    child, attr_name, target_value, max_depth, depth + 1
                )
                if found:
                    return found
        return None

    def _build_model(self, element: Any, depth: int = 0) -> AXElement:
        """Converts native reference to AXElement model."""
        return AXElement(
            role=self._get_attribute(element, "AXRole") or "Unknown",
            subrole=self._get_attribute(element, "AXSubrole"),
            title=self._get_attribute(element, "AXTitle"),
            description=self._get_attribute(element, "AXDescription"),
            identifier=self._get_attribute(element, "AXIdentifier"),
            value=self._get_attribute(element, "AXValue"),
            native_ref=element,
            depth=depth,
        )
