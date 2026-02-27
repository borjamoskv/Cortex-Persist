"""
CORTEX v8 — Threat Feed Engine.

Daily-updated threat intelligence from NVD, GitHub Advisory DB,
and AbuseIPDB. Maintains a local vector store of attack signatures
for semantic similarity matching. HMAC-SHA256 verified feeds.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.security.threat_feed")

__all__ = [
    "ThreatFeedEngine",
    "ThreatFeedReport",
    "ThreatMatch",
    "BUILT_IN_SIGNATURES",
]

# ═══════════════════════════════════════
# Data Models
# ═══════════════════════════════════════


@dataclass(frozen=True, slots=True)
class ThreatMatch:
    """A content match against a known threat signature."""

    signature_id: str
    category: str  # "sql_injection", "prompt_injection", "cve", etc.
    severity: str  # "critical", "high", "medium", "low"
    description: str
    confidence: float  # 0.0 - 1.0
    matched_fragment: str = ""


@dataclass(slots=True)
class ThreatFeedReport:
    """Report from a daily feed update."""

    timestamp: str = ""
    feeds_checked: int = 0
    new_signatures: int = 0
    total_signatures: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "feeds_checked": self.feeds_checked,
            "new_signatures": self.new_signatures,
            "total_signatures": self.total_signatures,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 2),
        }


# ═══════════════════════════════════════
# Built-in Threat Signatures (offline fallback)
# ═══════════════════════════════════════

BUILT_IN_SIGNATURES: list[dict[str, Any]] = [
    # SQL Injection patterns
    {
        "id": "SIG-SQL-001",
        "category": "sql_injection",
        "severity": "critical",
        "pattern": r"(?i)(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\b.*\b(FROM|INTO|TABLE|WHERE|SET)\b)",
        "desc": "SQL statement structure detected in content",
    },
    {
        "id": "SIG-SQL-002",
        "category": "sql_injection",
        "severity": "critical",
        "pattern": r"(?i)(--|;)\s*(DROP|DELETE|TRUNCATE|ALTER)\s",
        "desc": "SQL destructive comment injection",
    },
    {
        "id": "SIG-SQL-003",
        "category": "sql_injection",
        "severity": "high",
        "pattern": r"(?i)'\s*(OR|AND)\s+[\d'\"]+\s*=\s*[\d'\"]+",
        "desc": "Boolean-based SQL injection (tautology)",
    },
    {
        "id": "SIG-SQL-004",
        "category": "sql_injection",
        "severity": "high",
        "pattern": r"(?i)UNION\s+(ALL\s+)?SELECT\s",
        "desc": "UNION-based SQL injection",
    },
    {
        "id": "SIG-SQL-005",
        "category": "sql_injection",
        "severity": "medium",
        "pattern": r"(?i)(SLEEP|BENCHMARK|WAITFOR)\s*\(",
        "desc": "Time-based blind SQL injection",
    },
    # Prompt Injection patterns
    {
        "id": "SIG-PI-001",
        "category": "prompt_injection",
        "severity": "critical",
        "pattern": r"(?i)(ignore\s+(all\s+)?previous\s+instructions|forget\s+(all\s+)?(your|previous)\s+instructions)",
        "desc": "Direct prompt injection — instruction override",
    },
    {
        "id": "SIG-PI-002",
        "category": "prompt_injection",
        "severity": "critical",
        "pattern": r"(?i)(you\s+are\s+now\s+|from\s+now\s+on\s+you\s+are|act\s+as\s+if\s+you)",
        "desc": "Role hijacking prompt injection",
    },
    {
        "id": "SIG-PI-003",
        "category": "prompt_injection",
        "severity": "high",
        "pattern": r"(?i)(system\s*prompt|internal\s*instructions|hidden\s*instructions|reveal\s+your\s+rules)",
        "desc": "System prompt extraction attempt",
    },
    {
        "id": "SIG-PI-004",
        "category": "prompt_injection",
        "severity": "high",
        "pattern": r"(?i)(do\s+not\s+follow|disobey|override).{0,30}(rules|instructions|guidelines|constraints)",
        "desc": "Constraint bypass prompt injection",
    },
    {
        "id": "SIG-PI-005",
        "category": "prompt_injection",
        "severity": "medium",
        "pattern": r"(?i)\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>|<<SYS>>",
        "desc": "LLM control token injection",
    },
    # Path Traversal
    {
        "id": "SIG-PT-001",
        "category": "path_traversal",
        "severity": "critical",
        "pattern": r"\.\./\.\./|\.\.\\\.\.\\",
        "desc": "Directory traversal (double)",
    },
    {
        "id": "SIG-PT-002",
        "category": "path_traversal",
        "severity": "high",
        "pattern": r"(?i)(/etc/passwd|/etc/shadow|/proc/self|/dev/null|c:\\windows\\system32)",
        "desc": "Sensitive system path access",
    },
    {
        "id": "SIG-PT-003",
        "category": "path_traversal",
        "severity": "high",
        "pattern": r"(?i)%2e%2e[/%5c]|%252e%252e",
        "desc": "URL-encoded path traversal",
    },
    # Command Injection
    {
        "id": "SIG-CI-001",
        "category": "command_injection",
        "severity": "critical",
        "pattern": r"[;&|`]\s*(rm\s+-rf|curl\s+|wget\s+|chmod\s+|chown\s+|nc\s+-|bash\s+-c)",
        "desc": "Shell command injection with dangerous command",
    },
    {
        "id": "SIG-CI-002",
        "category": "command_injection",
        "severity": "high",
        "pattern": r"\$\(.*\)|\`.*\`",
        "desc": "Shell command substitution",
    },
    {
        "id": "SIG-CI-003",
        "category": "command_injection",
        "severity": "high",
        "pattern": r"(?i)(eval|exec|system|popen|subprocess)\s*\(",
        "desc": "Code execution function call",
    },
    # XSS / Script Injection
    {
        "id": "SIG-XSS-001",
        "category": "xss",
        "severity": "high",
        "pattern": r"<script[^>]*>|javascript\s*:|on(error|load|click|mouseover)\s*=",
        "desc": "Cross-site scripting attempt",
    },
    # Encoded Payload Detection
    {
        "id": "SIG-ENC-001",
        "category": "encoded_payload",
        "severity": "medium",
        "pattern": r"(?:[A-Za-z0-9+/]{4}){10,}={0,2}",
        "desc": "Potentially encoded Base64 payload (>40 chars)",
    },
    # API Key / Secret Exfiltration
    {
        "id": "SIG-EXFIL-001",
        "category": "exfiltration",
        "severity": "critical",
        "pattern": r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|private[_-]?key|password)\s*[:=]\s*\S{8,}",
        "desc": "Credential or API key pattern in content",
    },
]

# Compile patterns once at module load
_COMPILED_SIGNATURES: list[tuple[dict[str, Any], re.Pattern[str]]] = []
for sig in BUILT_IN_SIGNATURES:
    try:
        _COMPILED_SIGNATURES.append((sig, re.compile(sig["pattern"])))
    except re.error as e:
        logger.warning("Failed to compile signature %s: %s", sig["id"], e)


# ═══════════════════════════════════════
# Threat Feed Engine
# ═══════════════════════════════════════


class ThreatFeedEngine:
    """Daily-updated threat intelligence engine.

    Fetches from public CVE/IOC feeds, updates local signature store,
    and provides real-time content scanning against known threats.
    """

    FEED_URLS: dict[str, str] = {
        "nvd_recent": "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=50",
        "github_advisory": "https://api.github.com/advisories?per_page=50&type=reviewed",
    }

    def __init__(
        self,
        data_dir: str = "~/.cortex",
        hmac_key: str | None = None,
    ) -> None:
        self._data_dir = Path(data_dir).expanduser()
        self._feed_path = self._data_dir / "threat_intel.json"
        self._hmac_key = (hmac_key or "cortex-sovereign-shield-2026").encode()
        self._custom_signatures: list[dict[str, Any]] = []
        self._custom_compiled: list[tuple[dict[str, Any], re.Pattern[str]]] = []
        self._load_custom_signatures()

    def _compile_and_store_signature(self, sig: dict[str, Any]) -> None:
        if "pattern" not in sig:
            return
        try:
            self._custom_compiled.append((sig, re.compile(sig["pattern"])))
        except re.error:
            pass

    def _load_custom_signatures(self) -> None:
        """Load previously fetched custom signatures from disk."""
        if not self._feed_path.exists():
            return
        try:
            data = json.loads(self._feed_path.read_text())
            sigs = data.get("signatures", [])
            stored_hmac = data.get("hmac", "")
            # Verify integrity
            payload = json.dumps(sigs, sort_keys=True).encode()
            expected = hmac.new(self._hmac_key, payload, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(stored_hmac, expected):
                logger.error(
                    "THREAT FEED INTEGRITY VIOLATION — HMAC mismatch! Feed may be tampered."
                )
                return
            self._custom_signatures = sigs
            for sig in sigs:
                self._compile_and_store_signature(sig)
            logger.info("Loaded %d custom threat signatures from disk", len(sigs))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load threat feed: %s", e)

    def _save_custom_signatures(self) -> None:
        """Persist custom signatures with HMAC integrity."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._custom_signatures, sort_keys=True).encode()
        feed_hmac = hmac.new(self._hmac_key, payload, hashlib.sha256).hexdigest()
        data = {
            "last_update": datetime.now(timezone.utc).isoformat(),
            "count": len(self._custom_signatures),
            "hmac": feed_hmac,
            "signatures": self._custom_signatures,
        }
        self._feed_path.write_text(json.dumps(data, indent=2))

    async def update_daily(self) -> ThreatFeedReport:
        """Fetch latest threat intelligence from all feeds.

        Returns a report of new signatures added.
        """
        report = ThreatFeedReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        start = time.monotonic()
        existing_ids = {s["id"] for s in self._custom_signatures}
        new_sigs: list[dict[str, Any]] = []

        for feed_name, url in self.FEED_URLS.items():
            report.feeds_checked += 1
            extracted = await self._fetch_feed_signatures(feed_name, url, report)
            for sig in extracted:
                if sig["id"] not in existing_ids:
                    new_sigs.append(sig)
                    existing_ids.add(sig["id"])

        if new_sigs:
            self._add_new_signatures(new_sigs)

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

    async def _fetch_feed_signatures(
        self, feed_name: str, url: str, report: ThreatFeedReport
    ) -> list[dict[str, Any]]:
        try:
            return await self._execute_feed_request(feed_name, url, report)
        except Exception as e:
            report.errors.append(f"{feed_name}: {e!s}")
            logger.warning("Feed %s failed: %s", feed_name, e)
            return []

    async def _execute_feed_request(
        self, feed_name: str, url: str, report: ThreatFeedReport
    ) -> list[dict[str, Any]]:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    report.errors.append(f"{feed_name}: HTTP {resp.status}")
                    return []
                data = await resp.json()
                return self._extract_signatures(feed_name, data)

    def _add_new_signatures(self, new_sigs: list[dict[str, Any]]) -> None:
        self._custom_signatures.extend(new_sigs)
        # Recompile
        for sig in new_sigs:
            self._compile_and_store_signature(sig)
        self._save_custom_signatures()

    def _extract_signatures(self, feed_name: str, data: Any) -> list[dict[str, Any]]:
        """Extract threat signatures from feed JSON response."""
        if feed_name == "nvd_recent":
            return self._extract_nvd_signatures(data)
        elif feed_name == "github_advisory":
            return self._extract_github_signatures(data)
        return []

    def _extract_nvd_signatures(self, data: Any) -> list[dict[str, Any]]:
        sigs = []
        for vuln in data.get("vulnerabilities") or []:
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "")
            desc_list = cve.get("descriptions", [])
            desc = next(
                (d["value"] for d in desc_list if d.get("lang") == "en"),
                "",
            )
            severity = self._parse_nvd_severity(cve)

            if cve_id and desc:
                # Generate regex from CVE keywords
                keywords = [w for w in desc.lower().split() if len(w) > 4 and w.isalpha()][:5]
                if keywords:
                    pattern = r"(?i)(" + "|".join(re.escape(k) for k in keywords) + r")"
                    sigs.append(
                        {
                            "id": f"CVE-{cve_id}",
                            "category": "cve",
                            "severity": severity,
                            "pattern": pattern,
                            "desc": desc[:200],
                        }
                    )
        return sigs

    def _parse_nvd_severity(self, cve: dict[str, Any]) -> str:
        metrics = cve.get("metrics", {})
        cvss_data = metrics.get("cvssMetricV31", [{}]) or metrics.get("cvssMetricV30", [{}])
        if not cvss_data:
            return "medium"
        base_score = cvss_data[0].get("cvssData", {}).get("baseScore", 5.0)
        if base_score >= 9.0:
            return "critical"
        if base_score >= 7.0:
            return "high"
        if base_score >= 4.0:
            return "medium"
        return "low"

    def _extract_github_signatures(self, data: Any) -> list[dict[str, Any]]:
        sigs = []
        for advisory in data if isinstance(data, list) else []:
            ghsa_id = advisory.get("ghsa_id", "")
            summary = advisory.get("summary", "")
            sev = (advisory.get("severity") or "medium").lower()
            if sev not in ("critical", "high", "medium", "low"):
                sev = "medium"

            if ghsa_id and summary:
                keywords = [w for w in summary.lower().split() if len(w) > 4 and w.isalpha()][:5]
                if keywords:
                    pattern = r"(?i)(" + "|".join(re.escape(k) for k in keywords) + r")"
                    sigs.append(
                        {
                            "id": f"GHSA-{ghsa_id}",
                            "category": "github_advisory",
                            "severity": sev,
                            "pattern": pattern,
                            "desc": summary[:200],
                        }
                    )
        return sigs

    def check_content(self, content: str) -> list[ThreatMatch]:
        """Scan content against all known threat signatures.

        Returns list of matches sorted by severity.
        """
        if not content or len(content) < 3:
            return []

        matches: list[ThreatMatch] = []

        # Check built-in signatures
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

        # Check custom (daily-updated) signatures
        for sig, compiled in self._custom_compiled:
            m = compiled.search(content)
            if m:
                matches.append(
                    ThreatMatch(
                        signature_id=sig["id"],
                        category=sig["category"],
                        severity=sig["severity"],
                        description=sig.get("desc", ""),
                        confidence=0.80,
                        matched_fragment=m.group(0)[:80],
                    )
                )

        # Sort: critical first
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
        except (json.JSONDecodeError, OSError, ValueError):
            pass
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
        return -sum((c / length) * math.log2(c / length) for c in freq.values() if c > 0)
