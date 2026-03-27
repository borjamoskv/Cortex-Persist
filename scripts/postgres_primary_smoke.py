from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.engine.postgres_primary import PostgresPrimaryEngine
from cortex.routes.facts import router as facts_router
from cortex.routes.ledger import router as ledger_router
from cortex.routes.memories import router as memories_router
from cortex.routes.search import router as search_router
from cortex.storage.env import get_postgres_dsn
from cortex.storage.postgres import PostgresBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Exercise the public PostgreSQL vertical slice "
            "(store -> search -> vote -> checkpoint -> verify)."
        )
    )
    parser.add_argument("--dsn", help="PostgreSQL DSN. Defaults to CORTEX env aliases.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to write the smoke evidence report to.",
    )
    parser.add_argument(
        "--tenant-id",
        help="Tenant to use. Defaults to a unique smoke tenant.",
    )
    parser.add_argument(
        "--project",
        help="Project/namespace to use. Defaults to a unique smoke project.",
    )
    parser.add_argument(
        "--content",
        default="PostgreSQL smoke proof through the public API path",
        help="Fact content to store.",
    )
    parser.add_argument(
        "--query",
        default="smoke proof public API",
        help="Search query to validate recall.",
    )
    parser.add_argument(
        "--vote",
        type=int,
        default=1,
        choices=(-1, 0, 1),
        help="Vote value to record for the stored fact.",
    )
    return parser


def _mask_dsn(dsn: str) -> str:
    parts = urlsplit(dsn)
    host = parts.hostname or "unknown-host"
    port = f":{parts.port}" if parts.port else ""
    user = f"{parts.username}@" if parts.username else ""
    path = parts.path or ""
    return f"{parts.scheme}://{user}{host}{port}{path}"


def build_smoke_app(backend: PostgresBackend, tenant_id: str) -> FastAPI:
    app = FastAPI()
    app.state.primary_async_engine = PostgresPrimaryEngine(backend=backend)
    app.state.async_engine = None
    app.include_router(facts_router)
    app.include_router(memories_router)
    app.include_router(ledger_router)
    app.include_router(search_router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id=tenant_id,
        role="admin",
        permissions=["read", "write", "admin"],
        key_name="smoke-admin",
    )
    return app


def exercise_api_client(
    client: TestClient,
    *,
    project: str,
    content: str,
    query: str,
    vote: int = 1,
) -> dict[str, Any]:
    store_response = client.post(
        "/v1/memories",
        json={
            "project": project,
            "content": content,
            "type": "knowledge",
            "tags": ["postgres", "smoke"],
            "source": "smoke-script",
            "metadata": {"vertical": "store-ledger-query", "kind": "smoke"},
        },
    )
    store_payload = store_response.json()
    if store_response.status_code != 200:
        raise RuntimeError(f"Store failed: {store_response.status_code} {store_response.text}")

    stored_id = int(store_payload["id"])

    search_response = client.post(
        "/v1/search",
        json={"query": query, "k": 3, "project": project},
    )
    search_payload = search_response.json()
    if search_response.status_code != 200:
        raise RuntimeError(f"Search failed: {search_response.status_code} {search_response.text}")

    recall_response = client.get("/v1/memories", params={"project": project})
    recall_payload = recall_response.json()
    if recall_response.status_code != 200:
        raise RuntimeError(f"Recall failed: {recall_response.status_code} {recall_response.text}")

    vote_response = client.post(f"/v1/facts/{stored_id}/vote", json={"value": vote})
    vote_payload = vote_response.json()
    if vote_response.status_code != 200:
        raise RuntimeError(f"Vote failed: {vote_response.status_code} {vote_response.text}")

    checkpoint_response = client.post("/v1/ledger/checkpoint")
    checkpoint_payload = checkpoint_response.json()
    if checkpoint_response.status_code != 200:
        raise RuntimeError(
            f"Checkpoint failed: {checkpoint_response.status_code} {checkpoint_response.text}"
        )

    ledger_response = client.get("/v1/ledger/status")
    ledger_payload = ledger_response.json()
    if ledger_response.status_code != 200:
        raise RuntimeError(f"Ledger verify failed: {ledger_response.status_code} {ledger_response.text}")

    passed = (
        bool(search_payload)
        and bool(recall_payload)
        and ledger_payload.get("valid") is True
        and checkpoint_payload.get("checkpoint_id") is not None
        and checkpoint_payload.get("vote_checkpoint_id") is not None
    )

    return {
        "passed": passed,
        "store": {"status_code": store_response.status_code, "payload": store_payload},
        "search": {"status_code": search_response.status_code, "payload": search_payload},
        "recall": {"status_code": recall_response.status_code, "payload": recall_payload},
        "vote": {"status_code": vote_response.status_code, "payload": vote_payload},
        "checkpoint": {"status_code": checkpoint_response.status_code, "payload": checkpoint_payload},
        "ledger": {"status_code": ledger_response.status_code, "payload": ledger_payload},
    }


async def run_smoke(
    *,
    dsn: str,
    tenant_id: str | None,
    project: str | None,
    content: str,
    query: str,
    vote: int,
    output: Path | None,
) -> dict[str, Any]:
    resolved_tenant = tenant_id or f"tenant-pg-smoke-{uuid.uuid4().hex[:8]}"
    resolved_project = project or f"pg-smoke-{uuid.uuid4().hex[:8]}"
    backend = PostgresBackend(
        dsn=dsn,
        min_size=1,
        max_size=1,
        auto_init_schema=True,
    )
    await backend.connect()

    try:
        app = build_smoke_app(backend, resolved_tenant)
        with TestClient(app) as client:
            result = exercise_api_client(
                client,
                project=resolved_project,
                content=content,
                query=query,
                vote=vote,
            )
    finally:
        await backend.close()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": _mask_dsn(dsn),
        "tenant_id": resolved_tenant,
        "project": resolved_project,
        "content": content,
        "query": query,
        "vote": vote,
        **result,
    }

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return report


def main() -> int:
    args = build_parser().parse_args()
    dsn = args.dsn or get_postgres_dsn()
    if not dsn:
        print(
            "Missing PostgreSQL DSN. Set --dsn or one of: "
            "CORTEX_TEST_POSTGRES_DSN, POSTGRES_DSN, CORTEX_PG_DSN, "
            "CORTEX_PG_URL, DATABASE_URL, PG_URL.",
            file=sys.stderr,
        )
        return 2

    try:
        report = asyncio.run(
            run_smoke(
                dsn=dsn,
                tenant_id=args.tenant_id,
                project=args.project,
                content=args.content,
                query=args.query,
                vote=args.vote,
                output=args.output,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Smoke failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
