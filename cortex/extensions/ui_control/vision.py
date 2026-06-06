# [C5-REAL] Exergy-Maximized
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

try:
    import ImageIO
    import Quartz.CoreGraphics as CG
    from MobileCoreServices import kUTTypePNG
except ImportError:
    CG = None
    ImageIO = None
    kUTTypePNG = None

from cortex.extensions.ui_control.models import InteractionResult

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.extensions.ui_control.vision")


class VisionEngine:
    """
    Native screen capture and visual analysis bridge for macOS.
    Used for feedback loops and human-in-the-loop verification.
    """

    def __init__(self, engine: CortexEngine | None = None) -> None:
        self.engine = engine
        self._screenshots_dir = os.path.expanduser("~/.cortex/screenshots")
        os.makedirs(self._screenshots_dir, exist_ok=True)

    def capture_screen(self, region: tuple[int, int, int, int] | None = None) -> InteractionResult:
        """
        Captures the screen or a region and saves it to the CORTEX screenshots dir.
        Returns the path to the saved image.
        """
        if not CG:
            return InteractionResult(success=False, error="Quartz/CoreGraphics not available")

        # Create screenshot
        if region:
            rect = CG.CGRectMake(*region)
            image = CG.CGWindowListCreateImage(
                rect,
                CG.kCGWindowListOptionOnScreenOnly,
                CG.kCGNullWindowID,
                CG.kCGWindowImageDefault,
            )
        else:
            image = CG.CGDisplayCreateImage(CG.CGMainDisplayID())

        if not image:
            return InteractionResult(success=False, error="Failed to capture screen")

        # Save to file
        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.png"
        path = os.path.join(self._screenshots_dir, filename)

        url = CG.CFURLCreateWithFileSystemPath(None, path, CG.kCFURLPOSIXPathStyle, False)
        dest = ImageIO.CGImageDestinationCreateWithURL(url, kUTTypePNG, 1, None)

        if not dest:
            return InteractionResult(success=False, error="Failed to create image destination")

        ImageIO.CGImageDestinationAddImage(dest, image, None)
        if ImageIO.CGImageDestinationFinalize(dest):
            return InteractionResult(success=True, output=path)

        return InteractionResult(success=False, error="Failed to finalize image")

    def screenshot_region(self, x: int, y: int, width: int, height: int) -> bytes:
        """
        Captures a specific screen region and returns the raw PNG bytes.
        """
        if not CG:
            raise RuntimeError("Quartz/CoreGraphics not available")

        res = self.capture_screen(region=(x, y, width, height))
        if not res.success or not res.output:
            raise RuntimeError(f"Failed to capture region: {res.error}")

        filepath = res.output
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            if os.path.exists(filepath):
                os.remove(filepath)
            return data
        except Exception as e:
            raise RuntimeError(f"Failed to read screenshot file: {e}")
