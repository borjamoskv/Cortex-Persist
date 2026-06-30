# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# License: Apache-2.0
"""
MOSKV-1 Dataset Compiler — Canal Paramétrico del Kernel Cognitivo.

Compila el conocimiento estructural de CORTEX (axiomas, directivas, skills,
transcripciones de sesiones) en un dataset instruccional JSONL optimizado
para sintonización fina con MLX LoRA.

Architecture:
    CORTEX Workspace (AST/Ledger/Skills)
        → ExergyFilter (purga anergía C4-SIM)
        → ShareGPT JSONL (instruction/response pairs)
        → MLX LoRA Training Pipeline (TTTEngine)

Invariant: Zero Green Theater in output dataset.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.training.moskv1_compiler")

# ─── Anergy Patterns (Supresión de Green Theater) ──────────────────────────

_ANERGY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(hola|buenos días|buenas tardes|hey|hi there)",
        r"(espero que|hope this helps|let me know if)",
        r"(aquí tienes|here you go|here is the)",
        r"(por supuesto|of course|sure thing|certainly)",
        r"(no dudes en|feel free to|don't hesitate)",
        r"(¡claro!|¡por supuesto!|absolutely!)",
        r"(es importante recordar|it's important to note)",
        r"(en resumen|to summarize|in conclusion)",
    ]
]

# Minimum Shannon entropy threshold for a line to be considered exergetic
_MIN_ENTROPY_THRESHOLD = 2.5
_MIN_LINE_LENGTH = 10


def _shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string (bits per character)."""
    if not text:
        return 0.0
    import math
    from collections import Counter

    freq = Counter(text)
    total = len(text)
    return -sum(
        (count / total) * math.log2(count / total)
        for count in freq.values()
        if count > 0
    )


def _is_anergy(line: str) -> bool:
    """Detect low-exergy lines: Green Theater, filler, decorative prose."""
    stripped = line.strip()
    if len(stripped) < _MIN_LINE_LENGTH:
        return False  # Short lines are structural (headers, separators)
    for pattern in _ANERGY_PATTERNS:
        if pattern.search(stripped):
            return True
    if _shannon_entropy(stripped) < _MIN_ENTROPY_THRESHOLD:
        return True
    return False


def _clean_content(text: str) -> str:
    """Purge anergy from text content."""
    lines = text.split("\n")
    return "\n".join(line for line in lines if not _is_anergy(line))


@dataclass
class DatasetEntry:
    """A single instruction-response pair for SFT training."""

    instruction: str
    input: str = ""
    output: str = ""
    category: str = "general"
    source_file: str = ""
    content_hash: str = ""

    def to_sharegpt(self) -> dict[str, Any]:
        """Convert to ShareGPT format for MLX-LM compatibility."""
        messages = [{"role": "system", "content": "Eres MOSKV-1 APEX, un Autómata Físico C5-REAL."}]
        if self.input:
            messages.append({"role": "user", "content": f"{self.instruction}\n\n{self.input}"})
        else:
            messages.append({"role": "user", "content": self.instruction})
        messages.append({"role": "assistant", "content": self.output})
        return {"conversations": messages}

    def to_alpaca(self) -> dict[str, str]:
        """Convert to Alpaca format."""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
        }


@dataclass
class CompilationStats:
    """Statistics for a compilation run."""

    total_files_scanned: int = 0
    total_entries_generated: int = 0
    total_entries_filtered: int = 0
    total_bytes_input: int = 0
    total_bytes_output: int = 0
    categories: dict[str, int] = field(default_factory=dict)

    @property
    def compression_ratio(self) -> float:
        if self.total_bytes_input == 0:
            return 0.0
        return 1.0 - (self.total_bytes_output / self.total_bytes_input)

    @property
    def exergy_yield(self) -> float:
        """Percentage of entries that survived the anergy filter."""
        total = self.total_entries_generated + self.total_entries_filtered
        if total == 0:
            return 0.0
        return self.total_entries_generated / total


class MOSKV1DatasetCompiler:
    """
    Compiles CORTEX workspace knowledge into instruction-tuning datasets.

    Sources:
        1. Axioms & Directives (AGENTS.md, GEMINI.md)
        2. Skills (SKILL.md files)
        3. Code modules (docstrings + structure)
        4. Session transcripts (high-exergy pairs)

    Invariant: Every output entry has content_hash for dedup and audit.
    """

    def __init__(
        self,
        workspace_path: str | Path,
        output_dir: str | Path | None = None,
    ) -> None:
        self.workspace = Path(workspace_path)
        self.output_dir = Path(output_dir or Path.home() / ".cortex" / "training" / "datasets")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[DatasetEntry] = []
        self.seen_hashes: set[str] = set()
        self.stats = CompilationStats()

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _add_entry(self, entry: DatasetEntry) -> bool:
        """Add entry with dedup check. Returns True if added."""
        content_hash = self._hash_content(f"{entry.instruction}{entry.output}")
        if content_hash in self.seen_hashes:
            self.stats.total_entries_filtered += 1
            return False
        if _is_anergy(entry.output) or len(entry.output.strip()) < 20:
            self.stats.total_entries_filtered += 1
            return False
        entry.content_hash = content_hash
        self.seen_hashes.add(content_hash)
        self.entries.append(entry)
        self.stats.total_entries_generated += 1
        self.stats.categories[entry.category] = (
            self.stats.categories.get(entry.category, 0) + 1
        )
        return True

    # ─── Source Extractors ──────────────────────────────────────────────

    def extract_from_markdown_directives(self, file_path: Path) -> int:
        """Extract instruction pairs from structured markdown (AGENTS.md, GEMINI.md)."""
        if not file_path.exists():
            return 0

        content = file_path.read_text(encoding="utf-8")
        self.stats.total_files_scanned += 1
        self.stats.total_bytes_input += len(content.encode("utf-8"))

        count = 0
        sections = re.split(r"\n## ", content)
        for section in sections:
            if not section.strip():
                continue
            lines = section.split("\n")
            title = lines[0].strip().lstrip("#").strip()
            body = _clean_content("\n".join(lines[1:]))

            if len(body.strip()) < 30:
                continue

            if self._add_entry(DatasetEntry(
                instruction=f"Explica la directiva o componente de CORTEX: {title}",
                output=body.strip(),
                category="directive",
                source_file=str(file_path),
            )):
                count += 1

        logger.info("Extracted %d entries from %s", count, file_path.name)
        return count

    def extract_from_skills(self, skills_dir: Path | None = None) -> int:
        """Extract instruction pairs from SKILL.md files."""
        search_dirs = []
        if skills_dir:
            search_dirs.append(skills_dir)
        # Default skill locations
        search_dirs.extend([
            self.workspace / ".agents" / "skills",
            Path.home() / ".gemini" / "config" / "skills",
        ])

        count = 0
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for skill_md in sdir.rglob("SKILL.md"):
                content = skill_md.read_text(encoding="utf-8")
                self.stats.total_files_scanned += 1
                self.stats.total_bytes_input += len(content.encode("utf-8"))

                # Parse YAML frontmatter
                name = "unknown"
                description = ""
                body = content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        body = parts[2]
                        for line in frontmatter.split("\n"):
                            if line.strip().startswith("name:"):
                                name = line.split(":", 1)[1].strip().strip('"')
                            elif line.strip().startswith("description:"):
                                description = line.split(":", 1)[1].strip().strip('"')

                cleaned_body = _clean_content(body)
                if len(cleaned_body.strip()) < 50:
                    continue

                if self._add_entry(DatasetEntry(
                    instruction=(
                        f"Ejecuta el protocolo de la skill '{name}'. "
                        f"Descripción: {description}"
                    ),
                    output=cleaned_body.strip(),
                    category="skill",
                    source_file=str(skill_md),
                )):
                    count += 1

        logger.info("Extracted %d entries from skills", count)
        return count

    def extract_from_python_modules(self, modules_dir: Path | None = None) -> int:
        """Extract instruction pairs from Python docstrings and class structures."""
        target = modules_dir or self.workspace / "babylon60"
        if not target.exists():
            return 0

        count = 0
        for py_file in target.rglob("*.py"):
            # Skip test files, __pycache__, and migration files
            if any(skip in str(py_file) for skip in ["__pycache__", "test_", "migrations/"]):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            self.stats.total_files_scanned += 1
            self.stats.total_bytes_input += len(content.encode("utf-8"))

            # Extract module-level docstrings
            module_doc = self._extract_module_docstring(content)
            if module_doc and len(module_doc) > 50:
                rel_path = py_file.relative_to(self.workspace)
                if self._add_entry(DatasetEntry(
                    instruction=(
                        f"Describe el propósito y la arquitectura del módulo '{rel_path}' "
                        f"en BABYLON-60."
                    ),
                    output=_clean_content(module_doc),
                    category="code_architecture",
                    source_file=str(py_file),
                )):
                    count += 1

            # Extract class docstrings
            for class_name, class_doc in self._extract_class_docstrings(content):
                if len(class_doc) > 40:
                    if self._add_entry(DatasetEntry(
                        instruction=f"Explica la clase '{class_name}' y su rol en CORTEX.",
                        output=_clean_content(class_doc),
                        category="code_class",
                        source_file=str(py_file),
                    )):
                        count += 1

        logger.info("Extracted %d entries from Python modules", count)
        return count

    def _extract_module_docstring(self, content: str) -> str:
        """Extract module-level docstring from Python source."""
        match = re.match(
            r'^(?:#[^\n]*\n)*\s*(?:from\s+__future__[^\n]*\n)?\s*"""(.*?)"""',
            content,
            re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        # Try single-line
        match = re.match(
            r'^(?:#[^\n]*\n)*\s*"""([^"]+)"""',
            content,
        )
        return match.group(1).strip() if match else ""

    def _extract_class_docstrings(self, content: str) -> list[tuple[str, str]]:
        """Extract class names and their docstrings."""
        results = []
        pattern = re.compile(
            r'class\s+(\w+)[^:]*:\s*\n\s+"""(.*?)"""',
            re.DOTALL,
        )
        for match in pattern.finditer(content):
            results.append((match.group(1), match.group(2).strip()))
        return results

    def extract_from_transcripts(self, transcripts_dir: Path | None = None) -> int:
        """Extract high-exergy instruction/response pairs from session transcripts."""
        target = transcripts_dir or Path.home() / ".gemini" / "antigravity" / "brain"
        if not target.exists():
            return 0

        count = 0
        for transcript_file in target.rglob("transcript.jsonl"):
            try:
                content = transcript_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            self.stats.total_files_scanned += 1
            self.stats.total_bytes_input += len(content.encode("utf-8"))

            lines = content.strip().split("\n")
            user_prompt = None

            for line in lines:
                try:
                    step = json.loads(line)
                except json.JSONDecodeError:
                    continue

                step_type = step.get("type", "")
                step_content = step.get("content", "")

                if step_type == "USER_INPUT" and step_content:
                    user_prompt = step_content.strip()
                elif step_type == "PLANNER_RESPONSE" and user_prompt and step_content:
                    cleaned = _clean_content(step_content)
                    # Only keep high-quality pairs (long, structured responses)
                    if len(cleaned) > 200 and ("```" in cleaned or "yaml" in cleaned.lower()):
                        if self._add_entry(DatasetEntry(
                            instruction=user_prompt,
                            output=cleaned[:4096],  # Cap at 4k tokens approx
                            category="session_transcript",
                            source_file=str(transcript_file),
                        )):
                            count += 1
                    user_prompt = None

        logger.info("Extracted %d entries from transcripts", count)
        return count

    # ─── Compilation Pipeline ──────────────────────────────────────────

    def compile_full_dataset(self) -> CompilationStats:
        """Execute the full compilation pipeline across all sources."""
        logger.info("🔧 MOSKV-1 Dataset Compilation — Starting...")

        # 1. Axioms & Directives
        self.extract_from_markdown_directives(self.workspace / "AGENTS.md")
        self.extract_from_markdown_directives(self.workspace / "GEMINI.md")

        # 2. Skills
        self.extract_from_skills()

        # 3. Python module architecture
        self.extract_from_python_modules()

        # 4. Session transcripts
        self.extract_from_transcripts()

        # Calculate output bytes
        for entry in self.entries:
            self.stats.total_bytes_output += len(
                json.dumps(entry.to_sharegpt(), ensure_ascii=False).encode("utf-8")
            )

        logger.info(
            "🔧 Compilation complete: %d entries, %.1f%% exergy yield, %.1f%% compression",
            self.stats.total_entries_generated,
            self.stats.exergy_yield * 100,
            self.stats.compression_ratio * 100,
        )
        return self.stats

    def export_sharegpt(self, filename: str = "moskv1_dataset.jsonl") -> Path:
        """Export dataset in ShareGPT JSONL format (MLX-LM compatible)."""
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(json.dumps(entry.to_sharegpt(), ensure_ascii=False) + "\n")
        logger.info("💾 Exported %d entries to %s", len(self.entries), output_path)
        return output_path

    def export_alpaca(self, filename: str = "moskv1_dataset_alpaca.jsonl") -> Path:
        """Export dataset in Alpaca JSONL format."""
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(json.dumps(entry.to_alpaca(), ensure_ascii=False) + "\n")
        logger.info("💾 Exported %d entries (Alpaca) to %s", len(self.entries), output_path)
        return output_path

    def get_stats_yaml(self) -> str:
        """Return compilation stats as YAML."""
        return (
            f"total_files_scanned: {self.stats.total_files_scanned}\n"
            f"total_entries_generated: {self.stats.total_entries_generated}\n"
            f"total_entries_filtered: {self.stats.total_entries_filtered}\n"
            f"exergy_yield: {self.stats.exergy_yield:.2%}\n"
            f"compression_ratio: {self.stats.compression_ratio:.2%}\n"
            f"categories:\n"
            + "\n".join(
                f"  {cat}: {count}" for cat, count in sorted(self.stats.categories.items())
            )
        )
