"""CORTEX API — NotebookLM Routes.

Provides REST endpoints for NotebookLM Ouroboros memory loop operations:
  GET  /v1/notebooklm/status   → Staleness audit and file inventory
  POST /v1/notebooklm/digest   → Generate Master Digest
  POST /v1/notebooklm/fragment → Fragment by semantic domain
  POST /v1/notebooklm/sync     → Push to cloud provider
"""

from __future__ import annotations
from typing import Optional

from pathlib import Path

from fastapi import APIRouter, Depends, Query

from cortex.auth import AuthResult, require_permission

router = APIRouter(tags=["notebooklm"])


@router.get("/v1/notebooklm/status")
async def notebooklm_status(
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Get NotebookLM sync status — staleness, file inventory, cloud detection."""
    import os
    from datetime import datetime, timezone

    from cortex.services.notebooklm import CLOUD_PROVIDERS, DIGEST_FILE, DOMAINS_DIR

    result: dict = {}

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
    cloud = None
    for provider, paths in CLOUD_PROVIDERS.items():
        for p in paths:
            if p.parent.exists():
                cloud = {"provider": provider, "path": str(p)}
                break
        if cloud:
            break
    result["cloud"] = cloud or {"provider": "none"}

    # Staleness
    digest_info = result.get("digest", {})
    if digest_info.get("exists"):
        age = digest_info["age_hours"]
        if age > 48:
            result["staleness"] = "critical"
        elif age > 24:
            result["staleness"] = "warning"
        else:
            result["staleness"] = "fresh"
    else:
        result["staleness"] = "no_digest"

    return result


@router.post("/v1/notebooklm/digest")
async def notebooklm_digest(
    project: Optional[str] = Query(None, description="Optional project filter"),
    output: str = Query("cortex_notebooklm_digest.md", description="Output file path"),
    auth: AuthResult = Depends(require_permission("write")),
) -> dict:
    """Generate Master Digest with Shadow Key anchors."""
    from fastapi import HTTPException

    from cortex.config import DEFAULT_DB_PATH
    from cortex.services.notebooklm import NotebookLMService

    base_dir = Path.cwd().resolve()
    target_file = (base_dir / output).resolve()
    if not str(target_file).startswith(str(base_dir)):
        raise HTTPException(status_code=400, detail="Path traversal detected")

    svc = NotebookLMService(str(DEFAULT_DB_PATH))
    content = await svc.generate_digest(project=project)
    target_file.write_text(content, encoding="utf-8")
    word_count = len(content.split())

    return {
        "file": output,
        "facts_count": content.count("∆_CTX:"),
        "word_count": word_count,
        "status": "safe" if word_count < 500_000 else "OVER_LIMIT",
    }


@router.post("/v1/notebooklm/fragment")
async def notebooklm_fragment(
    output_dir: str = Query("notebooklm_domains", description="Output directory"),
    auth: AuthResult = Depends(require_permission("write")),
) -> dict:
    """Fragment CORTEX facts into semantic domain files."""
    from fastapi import HTTPException

    from cortex.config import DEFAULT_DB_PATH
    from cortex.services.notebooklm import NotebookLMService

    base_dir = Path.cwd().resolve()
    target_dir = (base_dir / output_dir).resolve()
    if not str(target_dir).startswith(str(base_dir)):
        raise HTTPException(status_code=400, detail="Path traversal detected")

    svc = NotebookLMService(str(DEFAULT_DB_PATH))
    counts = await svc.fragment_by_domain(target_dir)

    return {"domains": counts, "total_facts": sum(counts.values())}


@router.post("/v1/notebooklm/sync")
async def notebooklm_sync(
    drive_path: Optional[str] = Query(None, description="Explicit cloud folder path"),
    mode: str = Query("both", description="What to sync: digest, domains, or both"),
    auth: AuthResult = Depends(require_permission("write")),
) -> dict:
    """Sync exported files to cloud storage for NotebookLM pickup."""
    import os
    import shutil
    import time
    from datetime import datetime, timezone

    from cortex.services.notebooklm import CLOUD_PROVIDERS, DIGEST_FILE, DOMAINS_DIR

    target = None
    provider_name = "Custom"
    if drive_path:
        home = Path.home().resolve()
        requested = Path(drive_path).expanduser().resolve()
        if not str(requested).startswith(str(home)):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400, detail="Invalid drive_path. Must be within the home directory."
            )
        target = requested
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
        synced.append(dest.name)

    if mode in ("domains", "both") and DOMAINS_DIR.exists():
        for f in DOMAINS_DIR.glob("*.md"):
            dest = target / f.name
            shutil.copy2(f, dest)
            synced.append(dest.name)

    cutoff = time.time() - (7 * 86400)
    cleaned = 0
    synced_set = set(synced)
    for f in target.glob("*.md"):
        if os.path.getmtime(f) < cutoff and f.name not in synced_set:
            f.unlink()
            cleaned += 1

    return {
        "provider": provider_name,
        "destination": str(target),
        "files_synced": len(synced),
        "files_cleaned": cleaned,
    }
