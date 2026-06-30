# [C5-REAL] Exergy-Maximized
"""
Daemon Router.
"""

from babylon60.auth import AuthResult, require_permission
from babylon60.utils.i18n import get_trans
from fastapi import APIRouter, Depends, Request

__all__ = ["daemon_status"]

router = APIRouter(tags=["daemon"])


@router.get("/v1/daemon/status")
def daemon_status(request: Request, auth: AuthResult = Depends(require_permission("read"))) -> dict:
    """Get last daemon watchdog check results."""
    from babylon60.extensions.daemon import MoskvDaemon

    lang = request.headers.get("Accept-Language", "en")

    status = MoskvDaemon.load_status()
    if not status:
        return {"status": "no_data", "message": get_trans("error_daemon_no_data", lang)}
    return status
