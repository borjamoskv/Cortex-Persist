#!/usr/bin/env python3
"""Deployment orchestrator for Cortex-Persist.

This script validates runtime configuration, bootstraps local storage when
needed, emits a reproducible deployment manifest, and can launch the API
server with one command.

It intentionally stays small, dependency-light, and explicit:
- validate the environment
- initialize the schema
- write a deployment manifest
- serve the API when requested
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cortex.core import config as cortex_config
from stripe_config import (
    load_stripe_billing_config,
    validate_stripe_billing_config,
)

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema" / "events_log.sql"
MANIFEST_PATH = ROOT / "deploy.manifest.json"
LOGGER = logging.getLogger("cortex.deploy")


@dataclass(frozen=True)
class DeploymentReport:
    """Snapshot of the deployment state used for validation and manifests."""

    deploy_mode: str
    storage_mode: str
    database_url: str
    database_path: str
    stripe_enabled: bool
    stripe_configured: bool
    schema_path: str
    api_import: str
    git_sha: str | None = None
    issued_at: str | None = None


@dataclass(frozen=True)
class DeploymentIssue:
    """Human-readable deployment warning or blocking issue."""

    severity: str  # "warning" | "error"
    message: str


def _utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_sha() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def _schema_text() -> str:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing schema file: {SCHEMA_PATH}")
    return SCHEMA_PATH.read_text(encoding="utf-8")


def load_report() -> DeploymentReport:
    """Build a deployment report from the current environment."""
    cortex_config.reload()
    stripe_cfg = load_stripe_billing_config()
    database_url = cortex_config.PG_URL or os.environ.get("DATABASE_URL", "")

    return DeploymentReport(
        deploy_mode=cortex_config.DEPLOY_MODE,
        storage_mode=cortex_config.STORAGE_MODE,
        database_url=database_url,
        database_path=cortex_config.DB_PATH,
        stripe_enabled=bool(cortex_config.STRIPE_SECRET_KEY or cortex_config.STRIPE_WEBHOOK_SECRET),
        stripe_configured=not validate_stripe_billing_config(stripe_cfg),
        schema_path=str(SCHEMA_PATH),
        api_import="cortex.api:app",
        git_sha=_git_sha(),
        issued_at=_utcnow(),
    )


def validate_environment(strict: bool | None = None) -> list[DeploymentIssue]:
    """Validate runtime configuration and return blocking issues or warnings."""
    cortex_config.reload()
    issues: list[DeploymentIssue] = []

    production_mode = strict if strict is not None else cortex_config.DEPLOY_MODE == "cloud"
    stripe_cfg = load_stripe_billing_config()
    stripe_issues = validate_stripe_billing_config(stripe_cfg)

    if production_mode:
        required = {
            "STRIPE_SECRET_KEY": cortex_config.STRIPE_SECRET_KEY,
            "STRIPE_WEBHOOK_SECRET": cortex_config.STRIPE_WEBHOOK_SECRET,
            "STRIPE_PRICE_TABLE": json.dumps(cortex_config.STRIPE_PRICE_TABLE),
        }
        for key, value in required.items():
            if not value or value in {"{}", '{"pro": "", "team": ""}'}:
                issues.append(
                    DeploymentIssue(
                        severity="error",
                        message=f"Missing production env var: {key}",
                    )
                )

        if not (cortex_config.PG_URL or os.environ.get("DATABASE_URL")):
            issues.append(
                DeploymentIssue(
                    severity="error",
                    message="Production mode requires POSTGRES_DSN / CORTEX_PG_URL / DATABASE_URL.",
                )
            )

    for msg in stripe_issues:
        issues.append(DeploymentIssue(severity="error", message=msg))

    if cortex_config.STORAGE_MODE == "local" and not cortex_config.DB_PATH:
        issues.append(
            DeploymentIssue(
                severity="warning",
                message="Local storage selected but CORTEX_DB is empty; falling back to default path.",
            )
        )

    if not SCHEMA_PATH.exists():
        issues.append(
            DeploymentIssue(
                severity="error",
                message=f"Schema file not found: {SCHEMA_PATH}",
            )
        )

    return issues


def bootstrap_sqlite(database_path: str) -> Path:
    """Create or update the local SQLite database using the events log schema."""
    target = Path(database_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = _schema_text()
    with sqlite3.connect(target) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.executescript(schema_sql)
        conn.commit()

    return target


def bootstrap_postgres(dsn: str) -> None:
    """Apply the SQL schema to a Postgres database via psql.

    The function uses the native psql client to avoid hard-wiring an additional
    Python driver into the deployment tool.
    """
    if not dsn:
        raise ValueError("Postgres DSN is empty")

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing schema file: {SCHEMA_PATH}")

    try:
        subprocess.run(
            ["psql", dsn, "-f", str(SCHEMA_PATH)],
            cwd=ROOT,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("psql client not available in PATH") from exc


def write_manifest(report: DeploymentReport, target: str) -> Path:
    """Emit a reproducibility manifest for the deployment."""
    payload: dict[str, Any] = {
        **asdict(report),
        "target": target,
        "schema_sha256_hint": hash(_schema_text()),
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return MANIFEST_PATH


def serve(host: str, port: int, reload: bool = False) -> int:
    """Launch the API with uvicorn."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "cortex.api:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")

    completed = subprocess.run(cmd, cwd=ROOT)
    return int(completed.returncode)


def _print_report(report: DeploymentReport, issues: list[DeploymentIssue]) -> None:
    print(
        json.dumps(
            {
                "report": asdict(report),
                "issues": [asdict(issue) for issue in issues],
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Cortex-Persist deployment orchestrator")
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("validate", help="Validate runtime configuration")
    sub.add_parser("bootstrap-db", help="Bootstrap the local database schema")
    sub.add_parser("manifest", help="Write a deployment manifest JSON file")

    serve_parser = sub.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", default=8484, type=int)
    serve_parser.add_argument("--reload", action="store_true")

    args = parser.parse_args()
    command = args.command or "validate"

    report = load_report()
    issues = validate_environment()

    blocking = [issue for issue in issues if issue.severity == "error"]
    if command == "validate":
        _print_report(report, issues)
        return 1 if blocking else 0

    if blocking:
        _print_report(report, issues)
        return 1

    if command == "bootstrap-db":
        if cortex_config.STORAGE_MODE == "postgres" and report.database_url:
            bootstrap_postgres(report.database_url)
        else:
            bootstrap_sqlite(report.database_path)
        print(json.dumps({"status": "bootstrapped", "schema": str(SCHEMA_PATH)}, indent=2))
        return 0

    if command == "manifest":
        manifest_path = write_manifest(
            report, target="production" if cortex_config.PROD else "local"
        )
        print(json.dumps({"status": "written", "manifest": str(manifest_path)}, indent=2))
        return 0

    if command == "serve":
        if cortex_config.STORAGE_MODE == "local" and report.database_path:
            bootstrap_sqlite(report.database_path)
        elif cortex_config.STORAGE_MODE == "postgres" and report.database_url:
            LOGGER.info("Postgres schema should be applied externally or via bootstrap-db")

        write_manifest(report, target="production" if cortex_config.PROD else "local")
        return serve(args.host, args.port, reload=args.reload)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
