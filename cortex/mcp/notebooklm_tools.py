"""MCP tools for CORTEX NotebookLM integration.

Registers NotebookLM tools on a FastMCP server so AI agents
can manage the Ouroboros memory loop autonomously.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.mcp.notebooklm")


def register_notebooklm_tools(mcp: Any, ctx: Any) -> None:
    """Register NotebookLM tools on the MCP server.

    Args:
        mcp: FastMCP server instance.
        ctx: MCPContext with engine reference.
    """

    @mcp.tool()
    async def notebooklm_digest(
        output: str = "cortex_notebooklm_digest.md",
        project: str | None = None,
    ) -> dict:
        """Generate Master Digest for NotebookLM with Shadow Key anchors.

        Extracts all active CORTEX facts, applies the Shadow Key protocol
        (∆_CTX/∇_CTX anchors), and writes a cleartext Markdown digest.

        Args:
            output: Output file path (default: cortex_notebooklm_digest.md).
            project: Optional project filter. If None, exports all projects.

        Returns:
            dict with keys: file, facts_count, word_count, status.
        """
        from cortex.services.notebooklm import NotebookLMService

        db_path = getattr(ctx, "db_path", "")
        svc = NotebookLMService(str(db_path))
        content = await svc.generate_digest(project=project)

        Path(output).write_text(content, encoding="utf-8")
        word_count = len(content.split())
        facts_count = content.count("∆_CTX:")

        return {
            "file": output,
            "facts_count": facts_count,
            "word_count": word_count,
            "status": "safe" if word_count < 500_000 else "OVER_LIMIT",
        }

    @mcp.tool()
    async def notebooklm_fragment(
        output_dir: str = "notebooklm_domains",
    ) -> dict:
        """Fragment CORTEX facts into semantic domain files.

        Classifies facts by domain taxonomy (7 domains) and writes
        one timestamped Markdown file per domain.

        Args:
            output_dir: Output directory for domain fragment files.

        Returns:
            dict mapping domain name to fact count.
        """
        from cortex.services.notebooklm import NotebookLMService

        db_path = getattr(ctx, "db_path", "")
        svc = NotebookLMService(str(db_path))
        counts = await svc.fragment_by_domain(Path(output_dir))

        return {"domains": counts, "total_facts": sum(counts.values())}

    @mcp.tool()
    async def notebooklm_sync(
        drive_path: str | None = None,
        mode: str = "both",
    ) -> dict:
        """Sync exported files to cloud storage for NotebookLM pickup.

        Auto-detects Google Drive, OneDrive, or iCloud. Copies digest
        and/or domain fragments. Cleans stale files older than 7 days.

        Args:
            drive_path: Optional explicit cloud folder path. Auto-detected if None.
            mode: What to sync — 'digest', 'domains', or 'both'.

        Returns:
            dict with keys: provider, destination, files_synced, files_cleaned.
        """
        import os
        import shutil
        import time
        from datetime import datetime, timezone

        from cortex.services.notebooklm import CLOUD_PROVIDERS, DIGEST_FILE, DOMAINS_DIR

        # Detect provider
        target = None
        provider_name = "Custom"
        if drive_path:
            target = Path(drive_path)
        else:
            for provider, paths in CLOUD_PROVIDERS.items():
                for p in paths:
                    if p.parent.exists():
                        target = p
                        provider_name = provider
                        break
                if target:
                    break

        if not target:
            return {"error": "No cloud sync provider detected. Specify drive_path."}

        target.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        synced: list[str] = []

        if mode in ("digest", "both") and DIGEST_FILE.exists():
            dest = target / f"cortex-master-{ts}.md"
            shutil.copy2(DIGEST_FILE, dest)
            synced.append(str(dest))

        if mode in ("domains", "both") and DOMAINS_DIR.exists():
            for f in DOMAINS_DIR.glob("*.md"):
                dest = target / f.name
                shutil.copy2(f, dest)
                synced.append(str(dest))

        # Clean old files
        cutoff = time.time() - (7 * 86400)
        cleaned = 0
        synced_names = {Path(s).name for s in synced}
        for f in target.glob("*.md"):
            if os.path.getmtime(f) < cutoff and f.name not in synced_names:
                f.unlink()
                cleaned += 1

        return {
            "provider": provider_name,
            "destination": str(target),
            "files_synced": len(synced),
            "files_cleaned": cleaned,
        }

    @mcp.tool()
    async def notebooklm_status() -> dict:
        """Check NotebookLM sync status — staleness, file inventory, cloud detection.

        No arguments required. Reports digest freshness, domain fragment count,
        cloud sync provider availability, and staleness warnings.

        Returns:
            dict with keys: digest, domains, cloud, staleness.
        """
        import os
        from datetime import datetime, timezone

        from cortex.services.notebooklm import CLOUD_PROVIDERS, DIGEST_FILE, DOMAINS_DIR

        result: dict[str, Any] = {}

        # Digest status
        if DIGEST_FILE.exists():
            mtime = os.path.getmtime(DIGEST_FILE)
            age_h = (datetime.now(timezone.utc).timestamp() - mtime) / 3600
            result["digest"] = {
                "exists": True,
                "size_bytes": os.path.getsize(DIGEST_FILE),
                "updated": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                "age_hours": round(age_h, 1),
            }
        else:
            result["digest"] = {"exists": False}

        # Domain fragments
        if DOMAINS_DIR.exists():
            files = list(DOMAINS_DIR.glob("*.md"))
            result["domains"] = {
                "exists": True,
                "file_count": len(files),
                "total_bytes": sum(os.path.getsize(f) for f in files),
            }
        else:
            result["domains"] = {"exists": False}

        # Cloud detection
        cloud_detected = None
        for provider, paths in CLOUD_PROVIDERS.items():
            for p in paths:
                if p.parent.exists():
                    cloud_detected = {"provider": provider, "path": str(p)}
                    break
            if cloud_detected:
                break
        result["cloud"] = cloud_detected or {"provider": "none", "path": None}

        # Staleness
        if result["digest"].get("exists"):
            age = result["digest"]["age_hours"]
            if age > 48:
                result["staleness"] = "critical"
            elif age > 24:
                result["staleness"] = "warning"
            else:
                result["staleness"] = "fresh"
        else:
            result["staleness"] = "no_digest"

        return result

    logger.debug("Registered NotebookLM MCP tools")
