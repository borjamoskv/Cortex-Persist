"""
skills/deploy.py - Deploy skill: Event V1 wrapper for deploy.py logic.

Migration of deploy.py -> registry-bound skill.

IO contract:
    input:  EventV1(skill_id='deploy', payload={'command': str, ...options})
    output: dict artifact (JSON-serializable, no side effects outside artifact)

Supported commands via payload['command']:
    'validate'      - validate runtime config, return report + issues
    'bootstrap-db'  - bootstrap sqlite or postgres schema
    'manifest'      - write deploy.manifest.json, return manifest path
    'serve'         - launch uvicorn (blocking; use only in daemon context)

Registered as:
    @register('deploy', trigger_type='command_received')
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Registry import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skills.registry import register
from schema.event_v1 import EventV1

# Re-use existing deploy logic (no duplication)
# deploy.py lives at repo root and is kept for backward compat during cutover
try:
    import deploy as _deploy_module
    _DEPLOY_AVAILABLE = True
except ImportError:
    _DEPLOY_AVAILABLE = False

log = logging.getLogger(__name__)


class DeploySkillError(Exception):
    """Raised when deploy skill cannot execute."""


@register("deploy", trigger_type="command_received")
class DeploySkill:
    """
    Deploy skill: registry-bound wrapper over deploy.py orchestrator.

    execute() contract:
    - input: EventV1 with payload containing command + options
    - output: dict artifact (serializable, no sys.exit, no prints)
    - no side effects outside the returned artifact dict
    """

    def execute(self, event: EventV1) -> dict[str, Any]:
        """
        Dispatch deploy command from event payload.

        Args:
            event: EventV1 with payload:
                {
                    'command': 'validate' | 'bootstrap-db' | 'manifest' | 'serve',
                    'host': str (optional, for serve),
                    'port': int (optional, for serve),
                    'reload': bool (optional, for serve),
                    'strict': bool (optional, for validate),
                }

        Returns:
            dict artifact:
            {
                'command': str,
                'status': 'ok' | 'error' | 'blocked',
                'report': dict | None,
                'issues': list[dict],
                'detail': dict | None,
                'trace_id': str,
            }
        """
        command = event.payload.get("command", "validate")
        trace_id = event.trace_id

        log.info(f"DeploySkill: executing command='{command}' trace_id={trace_id}")

        if not _DEPLOY_AVAILABLE:
            return {
                "command": command,
                "status": "error",
                "report": None,
                "issues": [{"severity": "error", "message": "deploy module not available"}],
                "detail": None,
                "trace_id": trace_id,
            }

        # Load report + validate env
        try:
            report = _deploy_module.load_report()
            strict = event.payload.get("strict", None)
            issues = _deploy_module.validate_environment(strict=strict)
        except Exception as exc:
            return {
                "command": command,
                "status": "error",
                "report": None,
                "issues": [{"severity": "error", "message": str(exc)}],
                "detail": None,
                "trace_id": trace_id,
            }

        blocking = [i for i in issues if i.severity == "error"]
        report_dict = asdict(report)
        issues_dict = [asdict(i) for i in issues]

        # Validate only
        if command == "validate":
            return {
                "command": command,
                "status": "ok" if not blocking else "blocked",
                "report": report_dict,
                "issues": issues_dict,
                "detail": None,
                "trace_id": trace_id,
            }

        # Block on errors before any state mutation
        if blocking:
            return {
                "command": command,
                "status": "blocked",
                "report": report_dict,
                "issues": issues_dict,
                "detail": None,
                "trace_id": trace_id,
            }

        # bootstrap-db
        if command == "bootstrap-db":
            try:
                from cortex.core import config as cortex_config  # type: ignore
                if cortex_config.STORAGE_MODE == "postgres" and report.database_url:
                    _deploy_module.bootstrap_postgres(report.database_url)
                    detail = {"backend": "postgres", "dsn": report.database_url[:40] + "..."}
                else:
                    db_path = _deploy_module.bootstrap_sqlite(report.database_path)
                    detail = {"backend": "sqlite", "path": str(db_path)}

                return {
                    "command": command,
                    "status": "ok",
                    "report": report_dict,
                    "issues": issues_dict,
                    "detail": detail,
                    "trace_id": trace_id,
                }
            except Exception as exc:
                return {
                    "command": command,
                    "status": "error",
                    "report": report_dict,
                    "issues": issues_dict,
                    "detail": {"error": str(exc)},
                    "trace_id": trace_id,
                }

        # manifest
        if command == "manifest":
            try:
                from cortex.core import config as cortex_config  # type: ignore
                target = "production" if cortex_config.PROD else "local"
                manifest_path = _deploy_module.write_manifest(report, target=target)
                return {
                    "command": command,
                    "status": "ok",
                    "report": report_dict,
                    "issues": issues_dict,
                    "detail": {"manifest": str(manifest_path), "target": target},
                    "trace_id": trace_id,
                }
            except Exception as exc:
                return {
                    "command": command,
                    "status": "error",
                    "report": report_dict,
                    "issues": issues_dict,
                    "detail": {"error": str(exc)},
                    "trace_id": trace_id,
                }

        # serve — blocking, only use in daemon context
        if command == "serve":
            host = event.payload.get("host", "0.0.0.0")
            port = event.payload.get("port", 8484)
            reload = event.payload.get("reload", False)
            try:
                returncode = _deploy_module.serve(host=host, port=port, reload=reload)
                return {
                    "command": command,
                    "status": "ok" if returncode == 0 else "error",
                    "report": report_dict,
                    "issues": issues_dict,
                    "detail": {"host": host, "port": port, "returncode": returncode},
                    "trace_id": trace_id,
                }
            except Exception as exc:
                return {
                    "command": command,
                    "status": "error",
                    "report": report_dict,
                    "issues": issues_dict,
                    "detail": {"error": str(exc)},
                    "trace_id": trace_id,
                }

        # Unknown command
        return {
            "command": command,
            "status": "error",
            "report": report_dict,
            "issues": issues_dict,
            "detail": {"error": f"unknown command '{command}'"},
            "trace_id": trace_id,
        }
