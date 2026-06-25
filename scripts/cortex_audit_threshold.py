#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

@dataclass
class Finding:
    severity: str
    path: str
    reason: str
    score: Any = None
    details: dict[str, Any] | None = None

# Global lookup
MANIFEST_LOOKUP = {}

def load_manifest(root: Path):
    global MANIFEST_LOOKUP
    inv_path = root / "ANTI_GRAVITY" / "inventory.yaml"
    if inv_path.exists() and yaml is not None:
        try:
            data = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
            if data and "artifacts" in data:
                for art in data["artifacts"]:
                    # map absolute path strings to artifact metadata
                    new_p = str((root / art["new_path"]).resolve())
                    MANIFEST_LOOKUP[new_p] = art
        except Exception as e:
            print(f"Failed to load manifest: {e}")

def load_metadata(path: Path) -> dict[str, Any]:
    return MANIFEST_LOOKUP.get(str(path.resolve()), {})

def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_score(meta: dict[str, Any]) -> Any:
    for key in ("yield_score", "yieldScore", "score", "density_score"):
        if key in meta:
            return meta[key]
    return None

def as_float_score(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None

def iter_artifacts(root: Path):
    # Solamente iteramos sobre artefactos que han sido procesados por el inventario,
    # es decir, aquellos listados en MANIFEST_LOOKUP.
    for p_str in MANIFEST_LOOKUP.keys():
        p = Path(p_str)
        if p.exists() and p.is_file():
            yield p

def looks_like_active(path: Path) -> bool:
    return "01_ACTIVE" in path.parts

def looks_like_systems(path: Path) -> bool:
    return "02_SYSTEMS" in path.parts

def main() -> int:
    ap = argparse.ArgumentParser(description="MOSKV post-mutation threshold audit")
    ap.add_argument("--root", default=".", help="Repo root")
    ap.add_argument("--band-low", type=float, default=7.5)
    ap.add_argument("--band-high", type=float, default=8.5)
    ap.add_argument("--active-dir", default="ANTI_GRAVITY/01_ACTIVE")
    ap.add_argument("--systems-dir", default="ANTI_GRAVITY/02_SYSTEMS")
    ap.add_argument("--recent-hours", type=float, default=24.0)
    ap.add_argument("--min-size-active", type=int, default=1024)
    ap.add_argument("--json-report", default="")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    
    # Init manifest lookup
    load_manifest(root)

    (root / args.active_dir).resolve()
    (root / args.systems_dir).resolve()

    findings: list[Finding] = []
    hashes: dict[str, list[Path]] = {}
    
    for path in iter_artifacts(root):
        try:
            path.resolve()
            meta = load_metadata(path)
            raw_score = parse_score(meta)
            score = as_float_score(raw_score)
            size = path.stat().st_size
            mtime = path.stat().st_mtime
            
            import time
            file_age_hours = (time.time() - mtime) / 3600.0
            
        except Exception as e:
            findings.append(Finding(
                severity="ERROR",
                path=str(path),
                reason="unreadable artifact or metadata",
                details={"error": str(e)},
            ))
            continue

        # Hash index for duplicate detection
        try:
            digest = file_sha256(path)
            hashes.setdefault(digest, []).append(path)
        except Exception as e:
            findings.append(Finding(
                severity="WARN",
                path=str(path),
                reason="hashing failed",
                details={"error": str(e)},
            ))
            continue

        # Score validity
        if score is None:
            findings.append(Finding(
                severity="WARN",
                path=str(path),
                reason="missing or non-numeric yield_score",
                details={"metadata_keys": sorted(meta.keys())[:20]},
            ))
            continue

        # Boundary zone
        if args.band_low <= score <= args.band_high:
            findings.append(Finding(
                severity="WARN",
                path=str(path),
                reason="boundary-band artifact requires manual review",
                score=score,
                details={"band": [args.band_low, args.band_high]},
            ))

        # Route invariants
        in_active = looks_like_active(path)
        in_systems = looks_like_systems(path)

        if in_active and score < 8.0:
            findings.append(Finding(
                severity="ERROR",
                path=str(path),
                reason="low-score artifact found in 01_ACTIVE",
                score=score,
                details={"rule": "score < 8 in active surface"},
            ))

        if (not in_active) and score >= 8.0 and not in_systems:
            findings.append(Finding(
                severity="ERROR",
                path=str(path),
                reason="high-score artifact outside 01_ACTIVE/02_SYSTEMS",
                score=score,
                details={"rule": "score >= 8 must be surfaced or systemized"},
            ))

        if score >= 8.0 and file_age_hours < args.recent_hours:
            findings.append(Finding(
                severity="WARN",
                path=str(path),
                reason="high-score artifact modified too recently",
                score=score,
                details={"age_hours": round(file_age_hours, 3), "threshold_hours": args.recent_hours},
            ))

        # Size sanity: absurdly small but high score
        if score >= 8.0 and size < args.min_size_active:
            findings.append(Finding(
                severity="WARN",
                path=str(path),
                reason="high-score artifact is unusually small",
                score=score,
                details={"size_bytes": size, "min_size_bytes": args.min_size_active},
            ))

        # Explicit contradiction check from metadata, if present
        if "status" in meta and isinstance(meta["status"], str):
            s = meta["status"].lower()
            if score >= 8.0 and "archive" in s:
                findings.append(Finding(
                    severity="ERROR",
                    path=str(path),
                    reason="metadata says archive but score says active",
                    score=score,
                    details={"status": meta["status"]},
                ))

    # Duplicate detection
    for digest, paths in hashes.items():
        if len(paths) > 1:
            active_paths = [p for p in paths if looks_like_active(p)]
            if active_paths and len(paths) > 1:
                findings.append(Finding(
                    severity="ERROR",
                    path="; ".join(str(p) for p in paths),
                    reason="duplicate artifact hash across surfaces",
                    details={"sha256": digest, "count": len(paths)},
                ))

    # Emit report
    errors = [f for f in findings if f.severity == "ERROR"]
    warns = [f for f in findings if f.severity == "WARN"]

    summary = {
        "root": str(root),
        "band": [args.band_low, args.band_high],
        "findings": [asdict(f) for f in findings],
        "summary": {
            "errors": len(errors),
            "warns": len(warns),
            "total": len(findings),
        },
    }

    if args.json_report:
        Path(args.json_report).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary["summary"], indent=2))
    for f in findings:
        print(f"{f.severity}: {f.path} :: {f.reason}" + (f" :: score={f.score}" if f.score is not None else ""))

    # Hard fail on any error
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
