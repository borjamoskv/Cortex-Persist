from __future__ import annotations

import asyncio

from starlette.requests import Request

from cortex.auth.models import AuthResult
from cortex.routes.ledger import get_ledger_status


def test_ledger_status_maps_counts_and_scopes_tenant() -> None:
    observed: dict[str, str | None] = {}

    class FakeEngine:
        async def verify_ledger(self, tenant_id: str | None = None):
            observed["tx_tenant"] = tenant_id
            return {"valid": True, "violations": [], "tx_count": 3, "roots_checked": 2}

        async def verify_vote_ledger(self, tenant_id: str = "default"):
            observed["vote_tenant"] = tenant_id
            return {
                "valid": True,
                "violations": [],
                "votes_checked": 4,
                "checkpoints_checked": 1,
            }

    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 50000)})

    response = asyncio.run(
        get_ledger_status(
            request=request,
            auth=AuthResult(authenticated=True, tenant_id="tenant-a", permissions=["admin"]),
            engine=FakeEngine(),
        )
    )

    assert observed == {"tx_tenant": "tenant-a", "vote_tenant": "tenant-a"}
    assert response.valid is True
    assert response.tx_checked == 3
    assert response.roots_checked == 2
    assert response.votes_checked == 4
    assert response.vote_checkpoints_checked == 1
