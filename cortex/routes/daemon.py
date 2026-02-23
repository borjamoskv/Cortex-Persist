"""
CORTEX v5.0 — Daemon Router.
"""

from fastapi import APIRouter, Depends, Request

from cortex.auth import AuthResult, require_permission
from cortex.i18n import get_trans

__all__ = ['daemon_status']

router = APIRouter(tags=["daemon"])


@router.get("/v1/daemon/status")
def daemon_status(request: Request, auth: AuthResult = Depends(require_permission("read"))) -> dict:
    """Get last daemon watchdog check results."""
    from cortex.daemon import MoskvDaemon

    lang = request.headers.get("Accept-Language", "en")

    status = MoskvDaemon.load_status()
    if not status:
        return {"status": "no_data", "message": get_trans("error_daemon_no_data", lang)}
    return status
