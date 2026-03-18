"""Mac-Maestro-Ω — App Discovery (Target Lock phase)."""

from __future__ import annotations

import logging
import time

from .models import ActionFailed

logger = logging.getLogger("mac_maestro.app_discovery")

try:
    from AppKit import NSRunningApplication, NSWorkspace

    APPKIT_AVAILABLE = True
except ImportError:
    APPKIT_AVAILABLE = False


def _check_appkit() -> None:
    if not APPKIT_AVAILABLE:
        raise ActionFailed("AppKit not available. Install pyobjc-framework-Cocoa.")


def get_running_apps(bundle_id: str) -> list:
    """Return all running instances of an app by bundle_id."""
    _check_appkit()
    apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        bundle_id,
    )
    return list(apps) if apps else []


def get_pid(bundle_id: str) -> int:
    """Get PID of a running application."""
    apps = get_running_apps(bundle_id)
    if not apps:
        raise ActionFailed(f"App '{bundle_id}' is not running.")
    return apps[0].processIdentifier()


def get_app_name(bundle_id: str) -> str:
    """Get localized display name of a running application."""
    apps = get_running_apps(bundle_id)
    if not apps:
        raise ActionFailed(f"App '{bundle_id}' is not running.")
    return apps[0].localizedName() or bundle_id


def is_running(bundle_id: str) -> bool:
    """Check if an application is currently running."""
    try:
        return len(get_running_apps(bundle_id)) > 0
    except ActionFailed:
        return False


def is_frontmost(bundle_id: str) -> bool:
    """Check if an application is the frontmost application."""
    apps = get_running_apps(bundle_id)
    if not apps:
        return False
    return bool(apps[0].isActive())


def activate_app(bundle_id: str) -> bool:
    """Activate (bring to front) an application by bundle_id."""
    apps = get_running_apps(bundle_id)
    if not apps:
        raise ActionFailed(f"Cannot activate '{bundle_id}': not running.")
    return bool(apps[0].activateWithOptions_(0))


def get_frontmost_app() -> dict[str, str | int]:
    """Get the currently frontmost application as a dict."""
    _check_appkit()
    ws = NSWorkspace.sharedWorkspace()
    front = ws.frontmostApplication()
    if front is None:
        raise ActionFailed("No frontmost application detected.")
    return {
        "bundle_id": front.bundleIdentifier() or "unknown",
        "pid": front.processIdentifier(),
        "name": front.localizedName() or "unknown",
    }


def list_running_apps() -> list[dict[str, str | int]]:
    """List all running GUI applications with their bundle IDs and PIDs."""
    _check_appkit()
    ws = NSWorkspace.sharedWorkspace()
    apps = ws.runningApplications()
    result: list[dict[str, str | int]] = []
    for app in apps:
        # Only include apps with a bundle ID (skip background services)
        bundle = app.bundleIdentifier()
        if bundle:
            result.append({
                "name": app.localizedName() or "unknown",
                "bundle_id": bundle,
                "pid": app.processIdentifier(),
            })
    return sorted(result, key=lambda a: str(a.get("name", "")).lower())


def wait_for_app(bundle_id: str, timeout: float = 10.0) -> int:
    """Wait for an application to start running. Returns PID."""
    _check_appkit()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        apps = get_running_apps(bundle_id)
        if apps:
            return apps[0].processIdentifier()
        time.sleep(0.25)
    raise ActionFailed(f"App '{bundle_id}' did not start within {timeout}s.")

