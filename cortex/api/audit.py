"""
CORTEX v6 — Enterprise Audit Middleware.

Intercepts all API requests and logs them immutably into the
Enterprise Audit Ledger using PoQ-6 Standards (Privacy Shield).
"""

import logging
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response

logger = logging.getLogger("cortex.api_audit")


class SecurityAuditMiddleware:
    """FastAPI Middleware for strictly logging operations for SOC 2."""

    def __init__(self, ledger: Any) -> None:
        self.ledger = ledger

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process the request and immutably log the outcome."""
        start_time = time.time()

        # Privacy Shield: We do not log raw bodies containing secrets or PII.
        tenant_id = getattr(request.state, "tenant_id", "anonymous")
        actor_role = getattr(request.state, "role", "unknown")
        actor_id = getattr(request.state, "user_id", "unauthenticated")

        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            status_code = response.status_code
            status = "SUCCESS" if 200 <= status_code < 400 else f"FAILED_{status_code}"

        except Exception as e:  # deliberate boundary — middleware must capture all for audit log
            logger.error(f"Request failed: {e}")
            status = "CRASHED"
            raise

        finally:
            elapsed = time.time() - start_time
            # Commit to the immutable ledger
            if self.ledger:
                await self.ledger.log_action(
                    tenant_id=tenant_id,
                    actor_role=actor_role,
                    actor_id=actor_id,
                    action=method,
                    resource=path,
                    status=status,
                )
            else:
                logger.info(
                    "SOC 2 Audit: [%s] %s %s -> %s (T: %s|R: %s) in %.2fs",
                    status,
                    method,
                    path,
                    tenant_id,
                    actor_role,
                    actor_id,
                    elapsed,
                )

        return response
