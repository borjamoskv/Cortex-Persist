# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX - P0 Vulnerability Extractor.

Connects the Ouroboros-Omega DiagnosisMatrix (AST analysis) with the
Deepthink-R1 cluster for LLM-driven vulnerability hypothesis generation.

Architecture::

    DiagnosisMatrix (static AST)
        │
        ├─ Complexity hotspots (McCabe > 15)
        ├─ Deep nesting (> 4 levels)
        ├─ Dead code interfaces
        ├─ Blocking I/O patterns
        └─ Entropy score
        │
        ▼
    P0VulnerabilityExtractor
        │
        ├─ Builds structured prompt with code + matrix
        ├─ Dispatches to ThoughtOrchestra (DEEPTHINK_CLUSTER mode)
        ├─ Parses JSON findings from R1 reasoning chain
        └─ Returns list[P0Finding] with C1-C5 confidence

Invariants:
    - All findings are C3-Hypothetical or C4-Strong (never C5 without PoC)
    - Extractor is read-only - never modifies source code
    - Ω₉ compliance: output declares C4-SIMULACIÓN status
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex_extensions.evolution.p0_extractor")


# ─── Types ──────────────────────────────────────────────────────────────


class P0Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class P0Finding:
    """A single vulnerability hypothesis from the Deepthink cluster."""

    severity: P0Severity
    vector_type: str
    hypothesis: str
    code_evidence: str
    confidence: str = "C3-Hypothetical"
    function_name: str = ""
    line_range: str = ""
    requires_poc: bool = True
    reality_level: str = "C4-SIMULACIÓN"  # Ω₉ mandatory declaration


@dataclass
class P0Report:
    """Aggregated P0 extraction report."""

    target_file: str
    findings: list[P0Finding] = field(default_factory=list)
    entropy_score: float = 0.0
    complexity_hotspots: list[str] = field(default_factory=list)
    model_used: str = "unknown"
    status: str = "pending"
    reality_level: str = "C4-SIMULACIÓN"  # Ω₉

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == P0Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == P0Severity.HIGH)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_file": self.target_file,
            "findings": [asdict(f) for f in self.findings],
            "entropy_score": self.entropy_score,
            "complexity_hotspots": self.complexity_hotspots,
            "model_used": self.model_used,
            "status": self.status,
            "reality_level": self.reality_level,
            "summary": {
                "total": len(self.findings),
                "critical": self.critical_count,
                "high": self.high_count,
            },
        }


# ─── P0 Extractor ──────────────────────────────────────────────────────


class P0VulnerabilityExtractor:
    """Connects DiagnosisMatrix with Deepthink-R1 for vulnerability extraction.

    Usage::

        from babylon60.extensions.evolution.ouroboros_omega import OuroborosOmega
        from babylon60.extensions.evolution.p0_extractor import P0VulnerabilityExtractor

        engine = OuroborosOmega("target.py", dry_run=True)
        diagnosis = await engine.diagnose()

        extractor = P0VulnerabilityExtractor()
        report = await extractor.extract(
            source_code=engine.original_source,
            diagnosis=diagnosis,
            target_file="target.py",
        )

        for finding in report.findings:
            print(f"[{finding.severity}] {finding.hypothesis}")
    """

    # Maximum source code length to include in prompt (token budget guard)
    MAX_SOURCE_CHARS: int = 30_000

    def __init__(self, timeout_seconds: float = 120.0):
        self._timeout = timeout_seconds

    async def extract(
        self,
        source_code: str,
        diagnosis: Any,  # DiagnosisMatrix - use Any to avoid circular import
        target_file: str = "<unknown>",
    ) -> P0Report:
        """Run P0 vulnerability extraction via the Deepthink cluster.

        Args:
            source_code: The raw source code to analyze.
            diagnosis: DiagnosisMatrix from Ouroboros-Omega Phase 1.
            target_file: Path to the target file (for reporting).

        Returns:
            P0Report with findings and metadata.
        """
        report = P0Report(
            target_file=target_file,
            entropy_score=getattr(diagnosis, "entropy_score", 0.0),
        )

        # Identify complexity hotspots for focused analysis
        mccabe = getattr(diagnosis, "mccabe_complexity", {})
        hotspots = [f for f, c in mccabe.items() if c > 10]
        report.complexity_hotspots = hotspots

        # Build the analysis prompt
        prompt = self._build_prompt(source_code, diagnosis, target_file, hotspots)

        # Dispatch to Deepthink cluster
        try:
            raw_response = await self._dispatch_deepthink(prompt)
            findings = self._parse_findings(raw_response)
            report.findings = findings
            report.status = "completed"
            logger.info(
                "P0 extraction complete: %d findings (%d critical, %d high) for %s",
                len(findings),
                report.critical_count,
                report.high_count,
                target_file,
            )
        except Exception as e:
            logger.error("P0 extraction failed for %s: %s", target_file, e)
            report.status = f"failed: {e}"

        return report

    def _build_prompt(
        self,
        source_code: str,
        diagnosis: Any,
        target_file: str,
        hotspots: list[str],
    ) -> str:
        """Build the structured prompt for the Deepthink cluster."""
        # Truncate source if too long
        truncated = source_code[: self.MAX_SOURCE_CHARS]
        if len(source_code) > self.MAX_SOURCE_CHARS:
            truncated += (
                f"\n\n# ... TRUNCATED ({len(source_code) - self.MAX_SOURCE_CHARS} chars remaining)"
            )

        # Build diagnosis summary
        mccabe = getattr(diagnosis, "mccabe_complexity", {})
        nesting = getattr(diagnosis, "nesting_depths", {})
        dead = getattr(diagnosis, "dead_interfaces", set())
        blocking = getattr(diagnosis, "blocking_calls", [])
        entropy = getattr(diagnosis, "entropy_score", 0.0)
        loc = getattr(diagnosis, "loc", 0)

        diagnosis_block = (
            f"LOC: {loc}\n"
            f"Entropy Score: {entropy:.2f}/100\n"
            f"McCabe Complexity: {json.dumps(mccabe, default=str)}\n"
            f"Nesting Depths: {json.dumps(nesting, default=str)}\n"
            f"Dead Interfaces: {list(dead)}\n"
            f"Blocking I/O: {blocking}\n"
            f"Complexity Hotspots (McCabe > 10): {hotspots}"
        )

        return (
            f"## P0 Vulnerability Extraction - {target_file}\n\n"
            f"### DiagnosisMatrix (AST Analysis)\n```\n{diagnosis_block}\n```\n\n"
            f"### Source Code\n```python\n{truncated}\n```\n\n"
            "### Task\n"
            "Analyze the source code using the DiagnosisMatrix as a structural guide. "
            "Focus on complexity hotspots and functions with deep nesting. "
            "Generate vulnerability hypotheses as a JSON array. Each element must have:\n"
            '- "severity": "critical" | "high" | "medium" | "low"\n'
            '- "vector_type": one of "precision", "reentrancy", "access_control", '
            '"oracle", "logic", "overflow", "race_condition", "injection", "state_corruption"\n'
            '- "hypothesis": one sentence describing the vulnerability\n'
            '- "code_evidence": exact function name and line description\n'
            '- "confidence": "C3-Hypothetical" (unverified) or "C4-Strong" (structurally confirmed)\n'
            '- "function_name": name of the affected function\n\n'
            "Output ONLY the JSON array. No prose. No markdown fencing."
        )

    async def _dispatch_deepthink(self, prompt: str) -> str:
        """Dispatch the prompt to the Deepthink-R1 cluster via ThoughtOrchestra."""
        import asyncio

        try:
            from babylon60.extensions.thinking.orchestra import ThoughtOrchestra
            from babylon60.extensions.thinking.presets import OrchestraConfig

            config = OrchestraConfig(
                timeout_seconds=self._timeout,
                max_models=3,  # Cost-bounded: max 3 reasoning models
                dynamic_temperature=False,
                temperature=0.1,  # Low temp for deterministic extraction
            )

            async with ThoughtOrchestra(config=config) as orchestra:
                thought = await asyncio.wait_for(
                    orchestra.think(prompt, mode="deepthink_cluster"),
                    timeout=self._timeout,
                )
                self._last_model = thought.meta.get("winner", "deepthink_cluster")
                return thought.content

        except ImportError:
            logger.warning("ThoughtOrchestra unavailable - falling back to SovereignLLM")
            return await self._fallback_sovereign(prompt)

    async def _fallback_sovereign(self, prompt: str) -> str:
        """Fallback: use SovereignLLM directly if orchestra unavailable."""
        import asyncio

        from babylon60.extensions.llm.sovereign import SovereignLLM

        async with SovereignLLM(
            preferred_providers=["deepseek", "gemini", "openai"],
            temperature=0.1,
            max_tokens=4096,
            timeout_seconds=self._timeout,
            use_orchestra=False,
        ) as llm:
            result = await asyncio.wait_for(
                llm.generate(
                    prompt,
                    system=(
                        "You are a security-focused code analyzer. "
                        "Output vulnerability findings as a JSON array. "
                        "Each finding has: severity, vector_type, hypothesis, "
                        "code_evidence, confidence, function_name. "
                        "Output ONLY JSON. No prose."
                    ),
                    mode="deep_reasoning",
                ),
                timeout=self._timeout,
            )
            self._last_model = result.provider
            return result.content

    def _parse_findings(self, raw: str) -> list[P0Finding]:
        """Parse LLM response into P0Finding objects."""
        if not raw or not raw.strip():
            return []

        # Strip markdown fencing if present
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (fencing)
            if len(lines) > 2:
                content = "\n".join(lines[1:-1])

        # Try to extract JSON array
        try:
            # Find the JSON array in the response
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(content[start:end])
            else:
                data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse P0 findings JSON: %s", e)
            # Attempt line-by-line object extraction
            return self._fuzzy_parse(content)

        if not isinstance(data, list):
            data = [data]

        findings = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                severity_str = item.get("severity", "medium").lower()
                try:
                    severity = P0Severity(severity_str)
                except ValueError:
                    severity = P0Severity.MEDIUM

                findings.append(
                    P0Finding(
                        severity=severity,
                        vector_type=item.get("vector_type", "logic"),
                        hypothesis=item.get("hypothesis", ""),
                        code_evidence=item.get("code_evidence", ""),
                        confidence=item.get("confidence", "C3-Hypothetical"),
                        function_name=item.get("function_name", ""),
                        line_range=item.get("line_range", ""),
                    )
                )
            except (KeyError, TypeError) as e:
                logger.debug("Skipping malformed finding: %s", e)
                continue

        return findings

    def _fuzzy_parse(self, content: str) -> list[P0Finding]:
        """Last-resort: try to extract individual JSON objects from messy output."""
        findings = []
        depth = 0
        start = -1

        for i, char in enumerate(content):
            if char == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        obj = json.loads(content[start : i + 1])
                        severity_str = obj.get("severity", "medium").lower()
                        try:
                            severity = P0Severity(severity_str)
                        except ValueError:
                            severity = P0Severity.MEDIUM
                        findings.append(
                            P0Finding(
                                severity=severity,
                                vector_type=obj.get("vector_type", "logic"),
                                hypothesis=obj.get("hypothesis", ""),
                                code_evidence=obj.get("code_evidence", ""),
                                confidence=obj.get("confidence", "C3-Hypothetical"),
                                function_name=obj.get("function_name", ""),
                            )
                        )
                    except Exception as exc:
                        logger.warning("Suppressed exception: %s", exc)
                    start = -1

        return findings
