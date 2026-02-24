"""
CORTEX v5.0 — Dashboard Router.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from cortex.auth import AuthResult, require_permission

__all__ = ["router", "get_dashboard_html"]


def get_dashboard_html() -> str:
    '''Return the HTML payload for the dashboard.'''
    return r'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CORTEX Dashboard</title>
        <script>
            function sanitize(str) {
                if (!str) return '';
                return String(str).replace(/[&<>"']/g, function(m) {
                    return '&#' + m.charCodeAt(0) + ';';
                });
            }
            function renderFact(item) {
                return '<div class="fact">' + 
                       '<div>Project: ' + sanitize(item.project) + '</div>' + 
                       '<div>Type: ' + sanitize(item.fact_type) + '</div>' + 
                       '<div>Content: ' + sanitize(item.content) + '</div>' + 
                       '<div>Tags: ' + (item.tags ? item.tags.map(function(t) { return sanitize(t); }).join(', ') : '') + '</div></div>';
            }
        </script>
    </head>
    <body>
        <div id="app"></div>
    </body>
    </html>
    '''

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    auth: AuthResult = Depends(require_permission("read")),
) -> str:
    """Serve the embedded memory dashboard."""
    from cortex.routes.dashboard import get_dashboard_html

    return get_dashboard_html()
