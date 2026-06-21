"""
skills/repo_health.py - RepoHealth skill: Event V1 wrapper for repo_health_changed.py logic.

Migration of repo_health_changed.py -> registry-bound skill.

IO contract:
    input:  EventV1(skill_id='repo_health', payload={'command': str, ...options})
    output: dict artifact (JSON-serializable, no side effects outside artifact)

Supported commands via payload['command']:
    'check' - Check repo health for conflict markers and syntax errors.
              Options: 'files': list[str], 'all': bool, 'include_untracked': bool

Registered as:
    @register('repo_health', trigger_type='command_received')
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Registry import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skills.registry import register
from schema.event_v1 import EventV1

# Re-use existing repo_health logic (no duplication)
# The original script is in `scripts/`
scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    import repo_health_changed as _rh_module
    _RH_AVAILABLE = True
except ImportError:
    _RH_AVAILABLE = False

log = logging.getLogger(__name__)


@register("repo_health", trigger_type="command_received")
class RepoHealthSkill:
    """
    RepoHealth skill: registry-bound wrapper over repo_health_changed.py.

    execute() contract:
    - input: EventV1 with payload containing command + options
    - output: dict artifact (serializable)
    """

    def execute(self, event: EventV1) -> dict[str, Any]:
        command = event.payload.get("command", "check")
        trace_id = event.trace_id

        log.info(f"RepoHealthSkill: executing command='{command}' trace_id={trace_id}")

        if not _RH_AVAILABLE:
            return {
                "command": command,
                "status": "error",
                "report": None,
                "issues": [{"severity": "error", "message": "repo_health_changed module not available"}],
                "detail": None,
                "trace_id": trace_id,
            }

        if command == "check":
            files_arg = event.payload.get("files", [])
            all_arg = event.payload.get("all", False)
            include_untracked = event.payload.get("include_untracked", False)
            
            try:
                if files_arg:
                    files = [Path(item) for item in files_arg]
                elif all_arg:
                    files = _rh_module._all_repo_files()
                else:
                    files = _rh_module._changed_files_from_git(include_untracked=include_untracked)
                    
                targets = [path for path in files if path.exists() and path.is_file()]
            except Exception as exc:
                return {
                    "command": command,
                    "status": "error",
                    "report": None,
                    "issues": [{"severity": "error", "message": f"Failed to collect targets: {exc}"}],
                    "detail": None,
                    "trace_id": trace_id,
                }
                
            issues = []
            
            for path in targets:
                try:
                    marker_lines = _rh_module._text_contains_conflict_markers(path)
                    if marker_lines:
                        joined = ", ".join(str(line) for line in marker_lines[:10])
                        issues.append({
                            "severity": "error",
                            "message": f"Merge conflict markers at lines {joined}",
                            "file": str(path)
                        })

                    if path.suffix == ".py":
                        syntax_error = _rh_module._check_python_syntax(path)
                        if syntax_error:
                            issues.append({
                                "severity": "error",
                                "message": f"Syntax error: {syntax_error}",
                                "file": str(path)
                            })
                except Exception as exc:
                    issues.append({
                        "severity": "error",
                        "message": f"Exception checking file: {exc}",
                        "file": str(path)
                    })

            status = "ok" if not issues else "blocked"
            
            return {
                "command": command,
                "status": status,
                "report": {"targets_checked": len(targets)},
                "issues": issues,
                "detail": None,
                "trace_id": trace_id,
            }

        # Unknown command
        return {
            "command": command,
            "status": "error",
            "report": None,
            "issues": [],
            "detail": {"error": f"unknown command '{command}'"},
            "trace_id": trace_id,
        }
