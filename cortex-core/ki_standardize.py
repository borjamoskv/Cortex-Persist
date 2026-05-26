#!/usr/bin/env python3
"""
KI Schema Standardizer — One-shot normalizer for CORTEX Knowledge Items.

Fixes:
  - 80+ inconsistent field names → canonical 10-field schema
  - Missing `domain` → inferred from tags
  - Missing `last_accessed` → inferred from file atime
  - Missing `access_count` → initialized to 0
  - Oversized summaries → flagged (not auto-truncated)

Usage:
  python3 ki_standardize.py              # dry-run (default)
  python3 ki_standardize.py --apply      # apply changes
  python3 ki_standardize.py --report     # stats only
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

KI_BASE = Path.home() / ".gemini" / "antigravity" / "knowledge"

# Canonical schema
CANONICAL_FIELDS = {
    "title",
    "summary",
    "created_at",
    "updated_at",
    "last_accessed",
    "access_count",
    "status",
    "confidence",
    "tags",
    "domain",
    "references",
    "calibration",
}

# Timestamp field normalization map
TIMESTAMP_ALIASES = {
    "created": "created_at",
    "createdAt": "created_at",
    "date_created": "created_at",
    "date_added": "created_at",
    "crystallized_at": "created_at",
    "crawled_at": "created_at",
    "updated": "updated_at",
    "updatedAt": "updated_at",
    "date_updated": "updated_at",
    "last_updated": "updated_at",
    "lastModified": "updated_at",
    "lastAccessed": "last_accessed",
}

# Domain inference from tags (priority order)
DOMAIN_RULES = [
    ({"bounty", "immunefi", "code4rena"}, "security"),
    ({"security", "critical", "high"}, "security"),
    ({"cortex"}, "cortex"),
    ({"ai-agent", "ai-model"}, "ai"),
    ({"music", "sonic", "audio"}, "multimedia"),
    ({"design", "aesthetic"}, "design"),
    ({"philosophy"}, "philosophy"),
    ({"hardware"}, "hardware"),
    ({"web3", "blockchain", "defi"}, "web3"),
    ({"research"}, "research"),
    ({"infrastructure"}, "infrastructure"),
]

# Fields to preserve as-is (non-canonical but potentially useful)
PRESERVE_FIELDS = {
    "calibration",
    "capital_vector",
    "vulnerabilities",
    "poc_path",
    "poc_type",
    "pdr_hash",
}


def infer_domain(tags: list[str]) -> str:
    """Infer primary domain from tag set."""
    tag_set = set(t.lower() for t in tags)
    for trigger_tags, domain in DOMAIN_RULES:
        if tag_set & trigger_tags:
            return domain
    return "general"


def normalize_timestamp(value) -> str | None:
    """Normalize various timestamp formats to ISO8601."""
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        # Already ISO-ish
        return value
    return None


def standardize_ki(meta: dict, meta_path: Path, dry_run: bool = True) -> dict:
    """Standardize a single KI metadata dict. Returns the normalized version."""
    normalized = {}
    changes = []

    # 1. Title
    normalized["title"] = meta.get("title", meta.get("name", ""))

    # 2. Summary (preserve as-is, flag if oversized)
    normalized["summary"] = meta.get("summary", "")
    if len(normalized["summary"]) > 500:
        changes.append(f"  ⚠ summary={len(normalized['summary'])} chars (>500)")

    # 3. Timestamps — normalize aliases
    for alias, canonical in TIMESTAMP_ALIASES.items():
        if alias in meta and canonical not in normalized:
            ts = normalize_timestamp(meta[alias])
            if ts:
                normalized[canonical] = ts
                changes.append(f"  ✓ {alias} → {canonical}")

    # Preserve original canonical timestamps
    for ts_field in ("created_at", "updated_at", "last_accessed"):
        if ts_field in meta and ts_field not in normalized:
            normalized[ts_field] = meta[ts_field]

    # Fallback: use file timestamps
    stat = meta_path.stat()
    if "created_at" not in normalized:
        normalized["created_at"] = datetime.fromtimestamp(
            stat.st_birthtime if hasattr(stat, "st_birthtime") else stat.st_ctime, tz=timezone.utc
        ).isoformat()
        changes.append("  ✓ created_at ← file birthtime")

    if "updated_at" not in normalized:
        normalized["updated_at"] = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat()
        changes.append("  ✓ updated_at ← file mtime")

    if "last_accessed" not in normalized:
        normalized["last_accessed"] = datetime.fromtimestamp(
            stat.st_atime, tz=timezone.utc
        ).isoformat()
        changes.append("  ✓ last_accessed ← file atime")

    # 4. Access count
    normalized["access_count"] = meta.get("access_count", 0)

    # 5. Status & confidence
    normalized["status"] = meta.get("status", "active")
    normalized["confidence"] = meta.get("confidence", "C3")

    # 6. Tags
    normalized["tags"] = meta.get("tags", [])

    # 7. Domain — infer if missing
    if "domain" in meta:
        normalized["domain"] = meta["domain"]
    else:
        normalized["domain"] = infer_domain(normalized["tags"])
        changes.append(f"  ✓ domain inferred: {normalized['domain']}")

    # 8. References
    normalized["references"] = meta.get("references", [])

    # 9. Calibration (preserve)
    if "calibration" in meta:
        normalized["calibration"] = meta["calibration"]

    # 10. Preserve special fields
    for field in PRESERVE_FIELDS:
        if field in meta and field not in normalized:
            normalized[field] = meta[field]

    # Count dropped fields
    dropped = set(meta.keys()) - set(normalized.keys()) - CANONICAL_FIELDS
    dropped -= set(TIMESTAMP_ALIASES.keys())  # aliases already merged
    if dropped:
        changes.append(f"  ✗ dropped: {', '.join(sorted(dropped))}")

    return normalized, changes


def main():
    mode = "dry-run"
    if "--apply" in sys.argv:
        mode = "apply"
    elif "--report" in sys.argv:
        mode = "report"

    print(f"{'=' * 70}")
    print(f"KI SCHEMA STANDARDIZER — mode: {mode}")
    print(f"{'=' * 70}\n")

    if not KI_BASE.is_dir():
        print(f"ERROR: {KI_BASE} not found")
        sys.exit(1)

    stats = {
        "total": 0,
        "modified": 0,
        "errors": 0,
        "domains": Counter(),
        "oversized_summaries": 0,
        "fields_dropped": 0,
        "timestamps_normalized": 0,
        "domains_inferred": 0,
    }

    for ki_dir in sorted(KI_BASE.iterdir()):
        meta_path = ki_dir / "metadata.json"
        if not meta_path.is_file():
            continue

        stats["total"] += 1

        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR: {ki_dir.name}: {e}")
            stats["errors"] += 1
            continue

        normalized, changes = standardize_ki(meta, meta_path, dry_run=(mode != "apply"))

        stats["domains"][normalized.get("domain", "unknown")] += 1

        if changes:
            stats["modified"] += 1
            for c in changes:
                if "domain inferred" in c:
                    stats["domains_inferred"] += 1
                if "→" in c:
                    stats["timestamps_normalized"] += 1
                if "dropped" in c:
                    stats["fields_dropped"] += 1
                if "summary=" in c:
                    stats["oversized_summaries"] += 1

            if mode != "report":
                print(f"\n{ki_dir.name}:")
                for c in changes:
                    print(c)

            if mode == "apply":
                with open(meta_path, "w") as f:
                    json.dump(normalized, f, indent=2, ensure_ascii=False)
                    f.write("\n")

    # Report
    print(f"\n{'=' * 70}")
    print("RESULTS")
    print(f"{'=' * 70}")
    print(f"  Total KIs:              {stats['total']}")
    print(f"  Modified:               {stats['modified']}")
    print(f"  Errors:                 {stats['errors']}")
    print(f"  Timestamps normalized:  {stats['timestamps_normalized']}")
    print(f"  Domains inferred:       {stats['domains_inferred']}")
    print(f"  Oversized summaries:    {stats['oversized_summaries']}")
    print(f"  Fields dropped:         {stats['fields_dropped']}")
    print("\n  Domain distribution:")
    for domain, count in stats["domains"].most_common():
        print(f"    {domain:<20} {count:>4}")

    if mode == "dry-run":
        print("\n  → Run with --apply to write changes")
    elif mode == "apply":
        print(f"\n  ✓ Changes applied to {stats['modified']} KIs")


if __name__ == "__main__":
    main()
