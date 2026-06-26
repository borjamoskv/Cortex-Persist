# [C5-REAL] Exergy-Maximized
"""
PermsBootstrapper - macOS Permissions Bootstrapper.

Checks and requests OS-level permissions (Accessibility and Screen Recording)
required for low-level UI control.
"""

from __future__ import annotations

import logging
import sys

try:
    import ApplicationServices
    import Quartz
except ImportError:
    ApplicationServices = None
    Quartz = None

logger = logging.getLogger("cortex_extensions.ui_control.bootstrapper")


class PermsBootstrapper:
    """
    Handles verifying and prompting macOS system permissions
    for Accessibility and Screen Recording at boot time.
    """

    @staticmethod
    def verify_and_prompt_permissions() -> dict[str, bool]:
        """
        Verifies Accessibility and Screen Recording permissions.
        Prompts macOS system dialogs if permissions are missing.
        """
        status = {"accessibility": False, "screen_recording": False}

        if sys.platform != "darwin":
            logger.warning("Not running on macOS. Skipping permission bootstrapping.")
            return status

        if not ApplicationServices or not Quartz:
            logger.error(
                "Cocoa/Quartz/ApplicationServices not available. Cannot check permissions."
            )
            return status

        # 1. Check & Prompt Accessibility
        try:
            # AXIsProcessTrustedWithOptions prompts the user if not trusted
            options = {ApplicationServices.kAXTrustedCheckOptionPrompt: True}  # type: ignore
            trusted = ApplicationServices.AXIsProcessTrustedWithOptions(options)  # type: ignore
            status["accessibility"] = bool(trusted)
        except Exception as e:
            logger.error("Error checking accessibility permissions: %s", e)

        # 2. Check & Prompt Screen Recording (macOS Catalina 10.15+)
        try:
            if hasattr(Quartz, "CGPreflightScreenCaptureAccess"):
                has_rec = Quartz.CGPreflightScreenCaptureAccess()  # type: ignore
                status["screen_recording"] = bool(has_rec)
                if not has_rec:
                    logger.info("Screen Recording permission missing. Requesting access...")
                    Quartz.CGRequestScreenCaptureAccess()  # type: ignore
            else:
                # Fallback: check if we can capture a 1x1 region on main display
                rect = Quartz.CGRectMake(0, 0, 1, 1)  # type: ignore
                img = Quartz.CGWindowListCreateImage(  # type: ignore
                    rect,
                    Quartz.kCGWindowListOptionOnScreenOnly,  # type: ignore
                    Quartz.kCGNullWindowID,  # type: ignore
                    Quartz.kCGWindowImageDefault,  # type: ignore
                )
                status["screen_recording"] = img is not None
        except Exception as e:
            logger.error("Error checking screen recording permissions: %s", e)

        logger.info(
            "[Perms-Bootstrap] Accessibility: %s | Screen Recording: %s",
            "GRANTED" if status["accessibility"] else "DENIED",
            "GRANTED" if status["screen_recording"] else "DENIED",
        )

        return status
