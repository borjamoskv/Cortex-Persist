import logging
from typing import TYPE_CHECKING, Any, Optional

try:
    import ApplicationServices
    from AppKit import NSWorkspace
except ImportError:
    ApplicationServices = None
    NSWorkspace = None

from cortex.ui_control.models import AXElement, InteractionResult

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.ui_control.accessibility")

class AccessibilityEngine:
    """
    Direct bridge to macOS Accessibility APIs using PyObjC.
    Handles element inspection and interactions at the OS level.
    """

    def __init__(self, engine: Optional["CortexEngine"] = None) -> None:
        self.engine = engine

    def check_permissions(self) -> bool:
        """Verifies if the process has Accessibility permissions."""
        if not ApplicationServices:
            return False
        return ApplicationServices.AXIsProcessTrusted()

    def _get_app_element(self, app_name: str) -> Any | None:
        """Returns the base AXUIElement for a running application."""
        if not NSWorkspace:
            return None

        running_apps = NSWorkspace.sharedWorkspace().runningApplications()
        for app in running_apps:
            if app.localizedName() == app_name:
                return ApplicationServices.AXUIElementCreateApplication(app.processIdentifier())
        return None

    def find_element(self, app_name: str, identifier: str) -> AXElement | None:
        """
        Recursively searches for an element with a specific AXIdentifier.
        This is the preferred way to find elements as it's language-independent.
        """
        app_ref = self._get_app_element(app_name)
        if not app_ref:
            return None

        return self._search_recursive(app_ref, identifier)

    def _get_attribute(self, element: Any, attribute: str) -> Any:
        """Helper to safely retrieve an AX attribute."""
        error, value = ApplicationServices.AXUIElementCopyAttributeValue(element, attribute, None)
        if error == 0:
            return value
        return None

    def _search_recursive(self, element: Any, target_id: str) -> AXElement | None:
        """Internal recursive search for AXIdentifier."""
        # Check current element
        eid = self._get_attribute(element, "AXIdentifier")
        if eid == target_id:
            return self._build_model(element)

        # Get children
        children = self._get_attribute(element, "AXChildren")
        if not children:
            return None

        for child in children:
            found = self._search_recursive(child, target_id)
            if found:
                return found
        return None

    def _build_model(self, element: Any) -> AXElement:
        """Converts native reference to AXElement model."""
        return AXElement(
            role=self._get_attribute(element, "AXRole") or "Unknown",
            subrole=self._get_attribute(element, "AXSubrole"),
            title=self._get_attribute(element, "AXTitle"),
            description=self._get_attribute(element, "AXDescription"),
            identifier=self._get_attribute(element, "AXIdentifier"),
            native_ref=element
        )

    async def perform_click(self, element: AXElement) -> InteractionResult:
        """Performs a default action (click) on the element."""
        if not element.native_ref:
            return InteractionResult(success=False, error="No native reference found")

        error = ApplicationServices.AXUIElementPerformAction(
            element.native_ref, "AXPress", None
        )

        if error == 0:
            return InteractionResult(success=True)
        return InteractionResult(success=False, error=f"AXError: {error}")
