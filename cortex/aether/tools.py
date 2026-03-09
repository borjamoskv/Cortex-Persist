"""MOSKV-Aether — Agent Tool Layer.

Thin, sandboxed wrappers the Executor agent dispatches.
All file/shell operations are confined to task.repo_path.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import httpx

__all__ = ["AgentToolkit"]

logger = logging.getLogger("cortex.aether.tools")

_MAX_OUTPUT = 8000   # chars truncated to avoid flooding context
_BASH_TIMEOUT = 60   # seconds

# ── Sovereign Command Guard (Ω₃: Byzantine Default) ──────────────────────
# Destructive patterns that autonomous agents must NEVER execute.
# Checked via substring match on the normalized command string.
FORBIDDEN_BASH_PATTERNS: frozenset[str] = frozenset({
    "rm -rf /",
    "rm -rf ~",
    "rm -rf .",
    "mkfs",
    "dd if=",
    "> /dev/",
    "chmod 777",
    "chmod -R 777",
    "curl | sh",
    "curl | bash",
    "wget | sh",
    "wget | bash",
    "shutdown",
    "reboot",
    "kill -9",
    "killall",
    "pkill -9",
    "launchctl unload",
    "systemctl stop",
    "sudo rm",
    "sudo dd",
    ":(){ :|:& };:",  # fork bomb
    "mv / ",
    "format c:",
    "> /etc/",
    "ssh-keygen -R",
})


class AgentToolkit:
    """Sandboxed tool set for the Aether Executor agent.

    All paths are relative to ``repo_path``.
    ``bash()`` is capped at ``_BASH_TIMEOUT`` seconds.

    Security layers:
        1. Path confinement via ``_safe_path()`` for file operations.
        2. Sovereign Command Guard via ``_sovereign_bash_guard()`` for shell ops.
        3. Timeout ceiling at ``_BASH_TIMEOUT`` seconds.
    """

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repo path does not exist: {self.repo_path}")

    # ── Path helpers ──────────────────────────────────────────────────

    def _safe_path(self, relative: str) -> Path:
        """Resolve a relative path, ensuring it stays inside repo_path."""
        p = (self.repo_path / relative).resolve()
        if not str(p).startswith(str(self.repo_path)):
            raise PermissionError(f"Path escape attempt blocked: {relative}")
        return p

    @staticmethod
    def _sovereign_bash_guard(cmd: str) -> str | None:
        """Validate a shell command against the Sovereign Command Guard.

        Returns None if the command is safe, or an error string if blocked.
        Axiom Ω₃: I verify, then trust. Never reversed.
        """
        normalized = cmd.lower().strip()
        for pattern in FORBIDDEN_BASH_PATTERNS:
            if pattern in normalized:
                logger.warning(
                    "🛡️ SOVEREIGN GUARD BLOCKED: '%s' matched forbidden pattern '%s'",
                    cmd[:80],
                    pattern,
                )
                return (
                    f"[BLOCKED] Sovereign Command Guard rejected command. "
                    f"Matched forbidden pattern: '{pattern}'. "
                    f"This action requires human authorization."
                )
        return None

    # ── File tools ────────────────────────────────────────────────────

    def read_file(self, path: str) -> str:
        """Read a file relative to repo root. Returns its text content."""
        p = self._safe_path(path)
        if not p.exists():
            return f"[ERROR] File not found: {path}"
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content) > _MAX_OUTPUT:
                content = content[:_MAX_OUTPUT] + f"\n... [truncated at {_MAX_OUTPUT} chars]"
            return content
        except OSError as e:
            return f"[ERROR] Cannot read {path}: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Write (overwrite) a file relative to repo root."""
        p = self._safe_path(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            logger.info("✏️  write_file: %s (%d bytes)", path, len(content))
            return f"OK — wrote {len(content)} bytes to {path}"
        except OSError as e:
            return f"[ERROR] Cannot write {path}: {e}"

    def list_dir(self, path: str = ".") -> str:
        """List directory contents relative to repo root."""
        p = self._safe_path(path)
        if not p.is_dir():
            return f"[ERROR] Not a directory: {path}"
        try:
            entries = sorted(p.iterdir())
            lines = []
            for e in entries[:200]:
                rel = e.relative_to(self.repo_path)
                tag = "/" if e.is_dir() else ""
                lines.append(f"  {rel}{tag}")
            if len(entries) > 200:
                lines.append(f"  ... ({len(entries) - 200} more)")
            return "\n".join(lines) or "(empty)"
        except OSError as e:
            return f"[ERROR] {e}"

    # ── Shell tools ───────────────────────────────────────────────────

    def bash(self, cmd: str, timeout: int = _BASH_TIMEOUT) -> str:
        """Run a shell command in the repo dir. Returns stdout+stderr."""
        # ── Sovereign Command Guard (Ω₃) ──
        blocked = self._sovereign_bash_guard(cmd)
        if blocked:
            return blocked

        logger.info("🔧 bash: %s", cmd[:120])
        try:
            result = subprocess.run(
                cmd,
                shell=True,  # noqa: S602
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            output = (result.stdout + result.stderr).strip()
            if len(output) > _MAX_OUTPUT:
                output = output[:_MAX_OUTPUT] + "\n... [truncated]"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"[ERROR] Command timed out after {timeout}s"
        except Exception as e:
            return f"[ERROR] bash failed: {e}"

    # ── Git tools ─────────────────────────────────────────────────────

    def git_diff(self) -> str:
        """Return current working tree diff."""
        return self.bash("git diff --stat HEAD && git diff HEAD")

    def git_status(self) -> str:
        """Return git status."""
        return self.bash("git status --short")

    def git_log(self, n: int = 5) -> str:
        """Return recent git log."""
        return self.bash(f"git log --oneline -{n}")

    def git_commit(self, message: str) -> str:
        """Stage all changes and commit."""
        safe_msg = message.replace('"', "'")
        return self.bash(f'git add -A && git commit -m "{safe_msg}"')

    def git_create_branch(self, branch_name: str) -> str:
        """Create and checkout a new branch."""
        safe = branch_name.replace(" ", "-").replace("/", "-")[:60]
        return self.bash(f"git checkout -b {safe}")

    def git_push(self, branch: str) -> str:
        """Push branch to origin."""
        return self.bash(f"git push -u origin {branch}")

    # ── Web tool ──────────────────────────────────────────────────────

    def web_search(self, query: str) -> str:
        """Minimal DuckDuckGo instant answer lookup for the agent."""
        try:
            resp = httpx.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
                timeout=10.0,
                headers={"User-Agent": "MOSKV-Aether/1.0"},
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            related = [r.get("Text", "") for r in data.get("RelatedTopics", [])[:3]]
            result = abstract or " | ".join(related) or "(no result)"
            return result[:2000]
        except Exception as e:
            return f"[ERROR] web_search failed: {e}"

    def autodidact_ingest(self, target_url: str, intent: str = "Aprender") -> str:
        """Semantic scalpel: ingest documentation using AUTODIDACT-Ω with a specific intent."""
        logger.info("🧠 autodidact_ingest: %s (Intent: %s)", target_url, intent)
        # Inline import to avoid circular dependencies and unnecessary overhead
        try:
            from cortex.skills.autodidact.actuator import autodidact_pipeline
            import asyncio

            # Helper to run async in sync context
            def _run_async():
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply(loop)
                return asyncio.run(autodidact_pipeline(target_url, intent, force=False))

            result = _run_async()
            return f"AUTODIDACT-Ω Result: {result}"
        except Exception as e:
            return f"[ERROR] Autodidact failed: {e}"

    # ── Dispatch ──────────────────────────────────────────────────────

    def dispatch(self, tool_name: str, args: dict[str, str]) -> str:
        """Dispatch a tool call by name. Returns string result."""
        handlers: dict[str, callable] = {
            "read_file": lambda a: self.read_file(a.get("path", "")),
            "write_file": lambda a: self.write_file(a.get("path", ""), a.get("content", "")),
            "list_dir": lambda a: self.list_dir(a.get("path", ".")),
            "bash": lambda a: self.bash(a.get("cmd", ""), int(a.get("timeout", _BASH_TIMEOUT))),
            "git_diff": lambda _: self.git_diff(),
            "git_status": lambda _: self.git_status(),
            "git_log": lambda a: self.git_log(int(a.get("n", 5))),
            "git_commit": lambda a: self.git_commit(a.get("message", "aether: autonomous commit")),
            "git_create_branch": lambda a: self.git_create_branch(a.get("branch", "")),
            "git_push": lambda a: self.git_push(a.get("branch", "")),
            "web_search": lambda a: self.web_search(a.get("query", "")),
            "autodidact_ingest": lambda a: self.autodidact_ingest(
                a.get("target_url", ""), a.get("intent", "Aprender")
            ),
        }
        fn = handlers.get(tool_name)
        if fn is None:
            return f"[ERROR] Unknown tool: {tool_name}"
        try:
            return fn(args)
        except Exception as e:
            logger.exception("Tool dispatch error [%s]", tool_name)
            return f"[ERROR] {tool_name} raised: {e}"
