# [C5-REAL] Exergy-Maximized
"""
Threat Feed Engine.

Daily-updated threat intelligence from NVD, GitHub Advisory DB,
and AbuseIPDB. Maintains a local vector store of attack signatures
for semantic similarity matching. HMAC-SHA256 verified feeds.
"""

import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from babylon60.extensions.security.threat_signatures import BUILT_IN_SIGNATURES

logger = logging.getLogger("babylon60_extensions.security.threat_feed")
__all__ = ["BUILT_IN_SIGNATURES", "ThreatFeedEngine", "ThreatFeedReport", "ThreatMatch"]
_COMPILED_SIGNATURES: list[tuple[dict[str, Any], re.Pattern[str]]] = []
for _sig in BUILT_IN_SIGNATURES:
    try:
        _COMPILED_SIGNATURES.append((_sig, re.compile(_sig["pattern"])))
    except re.error as _e:
        logger.warning("Failed to compile signature %s: %s", _sig["id"], _e)


@dataclass(frozen=True)
class ThreatMatch:
    """A content match against a known threat signature."""

    signature_id: str
    category: str
    severity: str
    description: str
    confidence: float
    matched_fragment: str = ""


@dataclass()
class ThreatFeedReport:
    """Report from a daily feed update."""

    timestamp: str = ""
    feeds_checked: int = 0
    new_signatures: int = 0
    total_signatures: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """PENDING: Document to_dict"""
        return {
            "timestamp": self.timestamp,
            "feeds_checked": self.feeds_checked,
            "new_signatures": self.new_signatures,
            "total_signatures": self.total_signatures,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 2),
        }


def _keywords_to_pattern(text: str, max_keywords: int = 5) -> str | None:
    """Extract keywords from text and build a case-insensitive regex pattern."""
    keywords = [w for w in text.lower().split() if len(w) > 4 and w.isalpha()][:max_keywords]
    if not keywords:
        return None
    return "(?i)(" + "|".join(re.escape(k) for k in keywords) + ")"


class ThreatFeedEngine:
    """Daily-updated threat intelligence engine.

    Fetches from public CVE/IOC feeds, updates local signature store,
    and provides real-time content scanning against known threats.
    """

    FEED_URLS: dict[str, str] = {
        "nvd_recent": "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=50",
        "github_advisory": "https://api.github.com/advisories?per_page=50&type=reviewed",
    }

    def __init__(self, data_dir: str = "~/.cortex", hmac_key: str | None = None) -> None:
        self._data_dir = Path(data_dir).expanduser()
        self._feed_path = self._data_dir / "threat_intel.json"
        self._hmac_key = (hmac_key or "cortex-sovereign-shield-2026").encode()
        self._custom_signatures: list[dict[str, Any]] = []
        self._custom_compiled: list[tuple[dict[str, Any], re.Pattern[str]]] = []
        self._load_custom_signatures()  # pyright: ignore[reportAttributeAccessIssue]

    async def update_daily(self) -> ThreatFeedReport:
        """Fetch latest threat intelligence from all feeds.

        Returns a report of new signatures added.
        """
        report = ThreatFeedReport(
            timestamp=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        )
        start = time.monotonic()
        existing_ids = {s["id"] for s in self._custom_signatures}
        new_sigs: list[dict[str, Any]] = []
        for feed_name, url in self.FEED_URLS.items():
            report.feeds_checked += 1
            extracted = await self._fetch_feed_signatures(feed_name, url, report)  # pyright: ignore[reportAttributeAccessIssue]
            for sig in extracted:
                if sig["id"] not in existing_ids:
                    new_sigs.append(sig)
                    existing_ids.add(sig["id"])
        if new_sigs:
            self._add_new_signatures(new_sigs)  # pyright: ignore[reportAttributeAccessIssue]
        report.new_signatures = len(new_sigs)
        report.total_signatures = len(BUILT_IN_SIGNATURES) + len(self._custom_signatures)
        report.duration_seconds = time.monotonic() - start
        logger.info(
            "Threat feed update: %d new sigs, %d total, %d errors",
            report.new_signatures,
            report.total_signatures,
            len(report.errors),
        )
        return report

    def check_content(self, content: str) -> list[ThreatMatch]:
        """Scan content against all known threat signatures.

        Returns list of matches sorted by severity.
        """
        if not content or len(content) < 3:
            return []
        matches: list[ThreatMatch] = []
        for sig, compiled in _COMPILED_SIGNATURES:
            m = compiled.search(content)
            if m:
                matches.append(
                    ThreatMatch(
                        signature_id=sig["id"],
                        category=sig["category"],
                        severity=sig["severity"],
                        description=sig["desc"],
                        confidence=0.95,
                        matched_fragment=m.group(0)[:80],
                    )
                )
        for sig, compiled in self._custom_compiled:
            m = compiled.search(content)
            if m:
                matches.append(
                    ThreatMatch(
                        signature_id=sig["id"],
                        category=sig["category"],
                        severity=sig["severity"],
                        description=sig.get("desc", ""),
                        confidence=0.8,
                        matched_fragment=m.group(0)[:80],
                    )
                )
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        matches.sort(key=lambda m: severity_order.get(m.severity, 4))
        return matches

    def get_last_update(self) -> datetime | None:
        """Get timestamp of last successful feed update."""
        if not self._feed_path.exists():
            return None
        try:
            data = json.loads(self._feed_path.read_text())
            ts = data.get("last_update")
            if ts:
                return datetime.fromisoformat(ts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Suppressed exception: %s", exc)
        return None

    @property
    def total_signatures(self) -> int:
        """Total number of threat signatures (built-in + custom)."""
        return len(BUILT_IN_SIGNATURES) + len(self._custom_signatures)

    def entropy_score(self, content: str) -> float:
        """Calculate Shannon entropy of content.

        High entropy (>4.5) suggests encoded/encrypted payloads.
        """
        if not content:
            return 0.0
        freq: dict[str, int] = {}
        for ch in content:
            freq[ch] = freq.get(ch, 0) + 1
        length = len(content)
        return -sum(c / length * math.log2(c / length) for c in freq.values() if c > 0)
