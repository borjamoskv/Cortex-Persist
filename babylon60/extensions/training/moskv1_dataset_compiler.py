from __future__ import annotations
from decimal import Decimal
# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# License: Apache-2.0
"""
MOSKV-1 Dataset Compiler v2.0 — Canal Paramétrico del Kernel Cognitivo.

Compila el conocimiento estructural de CORTEX (axiomas, directivas, skills,
memory vault, workflows, ledger, transcripciones) en un dataset instruccional
JSONL optimizado para sintonización fina con MLX LoRA.

v2.0 Changes:
    - ExergyGuard reforzado (Shannon entropy + density scoring)
    - Memory Vault extraction (73+ archivos de conocimiento cristalizado)
    - Workflow extraction (.agents/workflows/)
    - Ledger fact extraction (sqlite DB queries)
    - Train/Val/Test split (80/10/10) requerido por MLX-LM
    - Instruction diversity via template rotation
    - Output length bounds [100, 4096] chars
    - HTML comment stripping in markdown parser
    - Per-entry exergy scoring for quality ranking

Invariant: Zero Green Theater in output dataset.
"""


import hashlib
import json
import logging
import math
import os
import random
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("babylon60.training.moskv1_compiler")

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
        r"(como puedes ver|as you can see)",
        r"(vale la pena|it's worth noting)",
        r"(me alegra|I'm glad|I'm happy to)",
        r"(sin más preámbulos|without further ado)",
        r"(recuerda que|remember that|keep in mind)",
        r"^(ok,?\s|okay,?\s|alright,?\s)",
        r"(básicamente|basically|essentially)",
    ]
]

# HTML comment pattern for stripping
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# System-injected XML tags from transcripts
_SYSTEM_XML_TAGS_RE = re.compile(
    r"<(?:USER_REQUEST|/USER_REQUEST|ADDITIONAL_METADATA|/ADDITIONAL_METADATA"
    r"|USER_SETTINGS_CHANGE|/USER_SETTINGS_CHANGE|SYSTEM_MESSAGE|/SYSTEM_MESSAGE"
    r"|conversation_summaries|/conversation_summaries)[^>]*>",
    re.IGNORECASE,
)


def _clean_transcript_prompt(text: str) -> str:
    """Strip system-injected XML metadata from transcript user prompts."""
    # Remove XML tags
    cleaned = _SYSTEM_XML_TAGS_RE.sub("", text)
    cleaned = _HTML_COMMENT_RE.sub("", cleaned)
    # Remove lines that are pure metadata
    lines = cleaned.split("\n")
    filtered = []
    skip_block = False
    for line in lines:
        stripped = line.strip()
        # Skip metadata blocks
        if stripped.startswith("The current local time is:"):
            continue
        if stripped.startswith("The user changed setting"):
            continue
        if stripped.startswith("# Conversation History"):
            skip_block = True
            continue
        if skip_block and stripped.startswith("## Conversation "):
            continue
        if skip_block and not stripped:
            skip_block = False
            continue
        if not skip_block and stripped:
            filtered.append(line)
    return "\n".join(filtered).strip()


# Minimum thresholds
_MIN_ENTROPY_THRESHOLD = 2.8
_MIN_LINE_LENGTH = 12
_MIN_OUTPUT_LENGTH = 100
_MAX_OUTPUT_LENGTH = 2000
_MIN_INSTRUCTION_LENGTH = 15

# ─── Instruction Templates (Diversity) ─────────────────────────────────────

_DIRECTIVE_TEMPLATES = [
    "Explica e implementa la directiva de CORTEX: {title}",
    "¿Cuál es el propósito y la mecánica operacional de '{title}' en BABYLON-60?",
    "Describe la invariante '{title}' y cómo se aplica en el runtime de CORTEX.",
    "Como MOSKV-1, ejecuta un análisis estructural de: {title}",
    "Detalla la especificación técnica de '{title}' dentro del ecosistema BABYLON-60.",
]

_CODE_MODULE_TEMPLATES = [
    "Describe el propósito y la arquitectura del módulo '{path}' en BABYLON-60.",
    "¿Qué responsabilidades tiene '{path}' dentro del sistema CORTEX?",
    "Analiza la estructura del módulo '{path}' y su rol en el pipeline de ejecución.",
    "Como Persist-Auditor, documenta las invariantes del módulo '{path}'.",
]

_CODE_CLASS_TEMPLATES = [
    "Explica la clase '{name}' y su rol en el sistema CORTEX.",
    "¿Cuál es la responsabilidad de '{name}' dentro de la arquitectura BABYLON-60?",
    "Documenta la interfaz pública y las invariantes de la clase '{name}'.",
    "Describe cómo '{name}' interactúa con otros componentes del sistema.",
]

_SKILL_TEMPLATES = [
    "Ejecuta el protocolo de la skill '{name}': {description}",
    "¿Cómo se invoca y qué produce la skill '{name}'?",
    "Describe la mecánica de ejecución de '{name}' ({description}).",
]

_VAULT_TEMPLATES = [
    "Recupera y sintetiza el conocimiento persistido en: {title}",
    "¿Qué información contiene el registro del Memory Vault sobre '{title}'?",
    "Expande el contexto de la entrada de memoria: {title}",
]

_WORKFLOW_TEMPLATES = [
    "Ejecuta el workflow '{name}': {description}",
    "¿Cuáles son los pasos del protocolo '{name}'?",
    "Describe el flujo de ejecución del workflow '{name}' ({description}).",
]


def _pick_template(templates: list[str], **kwargs: str) -> str:
    """Select a random template and format it."""
    return random.choice(templates).format(**kwargs)


# ─── Entropy & Quality Scoring ──────────────────────────────────────────────


def _shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string (bits per character)."""
    if not text:
        return 0.0
    freq = Counter(text)
    total = len(text)
    log2_total = math.log2(total)
    sum_terms = sum(count * math.log2(count) for count in freq.values() if count > 0)
    return log2_total - (sum_terms / total)


def _exergy_score(text: str) -> float:
    """
    Calculate exergy score [0.0, 1.0] for a text block.

    Factors:
        - Shannon entropy (information density)
        - Code block ratio (structural content)
        - Unique token ratio (vocabulary richness)
        - Line structure ratio (formatted vs prose)
    """
    if not text or len(text) < 20:
        return 0.0

    entropy = _shannon_entropy(text)
    entropy_score = min(entropy / 5.0, 1.0)  # Normalize to [0, 1]

    # Code block density
    code_blocks = text.count("```")
    code_score = min(code_blocks / 4.0, 1.0)

    # Structural markers (YAML, lists, headers)
    structural_markers = (
        text.count("\n- ")
        + text.count("\n* ")
        + text.count("\n| ")
        + text.count(":\n")
        + text.count("\n## ")
        + text.count("\n### ")
    )
    structure_score = min(structural_markers / 10.0, 1.0)

    # Unique token ratio (vocabulary richness)
    tokens = text.lower().split()
    unique_ratio = len(set(tokens)) / max(len(tokens), 1)

    return entropy_score * 0.3 + code_score * 0.25 + structure_score * 0.25 + unique_ratio * 0.2


def _is_anergy(line: str) -> bool:
    """Detect low-exergy lines: Green Theater, filler, decorative prose."""
    stripped = line.strip()
    if len(stripped) < _MIN_LINE_LENGTH:
        return False  # Short lines are structural (headers, separators)
    for pattern in _ANERGY_PATTERNS:
        if pattern.search(stripped):
            return True
    # Only apply entropy check to longer prose lines (not code/yaml)
    if not stripped.startswith(("-", "*", "|", "#", "`", "def ", "class ", "import ")):
        if _shannon_entropy(stripped) < _MIN_ENTROPY_THRESHOLD and len(stripped) > 50:
            return True
    return False


def _clean_content(text: str) -> str:
    """Purge anergy and HTML comments from text content."""
    # Strip HTML comments first
    text = _HTML_COMMENT_RE.sub("", text)
    lines = text.split("\n")
    cleaned = [line for line in lines if not _is_anergy(line)]
    # Remove excessive blank lines
    result = []
    blank_count = 0
    for line in cleaned:
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result).strip()


def _truncate_output(text: str, max_length: int = _MAX_OUTPUT_LENGTH) -> str:
    """Truncate output to max_length, preserving complete blocks and closing code blocks."""
    if len(text) <= max_length:
        return text
    # Try to cut at a paragraph boundary
    truncated = text[:max_length]
    last_double_newline = truncated.rfind("\n\n")
    if last_double_newline > max_length * 0.6:
        res = truncated[:last_double_newline].strip()
    else:
        # Cut at last complete line
        last_newline = truncated.rfind("\n")
        if last_newline > max_length * 0.8:
            res = truncated[:last_newline].strip()
        else:
            res = truncated.strip()

    # Ensure open markdown code blocks are closed to preserve syntax validity
    if res.count("```") % 2 != 0:
        res += "\n```"
    return res


# ─── Data Models ────────────────────────────────────────────────────────────


@dataclass
class DatasetEntry:
    """A single instruction-response pair for SFT training."""

    instruction: str
    input: str = ""
    output: str = ""
    category: str = "general"
    source_file: str = ""
    content_hash: str = ""
    exergy_score: Decimal = 0.0

    def to_sharegpt(self) -> dict[str, Any]:
        """Convert to ShareGPT format for MLX-LM compatibility."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres MOSKV-1 APEX, un Autómata Físico C5-REAL. "
                    "Cero anergía. Justificación densa. "
                    "Output en YAML/código/diffs. Sin saludos ni prosa decorativa. "
                    "Firma: borjamoskv."
                ),
            }
        ]
        user_content = f"{self.instruction}\n\n{self.input}" if self.input else self.instruction
        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": self.output})
        return {"messages": messages}

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
    filter_reasons: dict[str, int] = field(default_factory=dict)
    avg_exergy_score: Decimal = 0.0

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

    Sources (v2.0):
        1. Axioms & Directives (AGENTS.md, GEMINI.md)
        2. Skills (SKILL.md files)
        3. Code modules (docstrings + structure)
        4. Session transcripts (high-exergy pairs)
        5. Memory Vault (~/.gemini/config/.cortex/memory_vault/)
        6. Workflows (.agents/workflows/)
        7. Ledger facts (sqlite DB)

    Invariants:
        - Every output entry has content_hash for dedup and audit
        - Output length bounded [100, 4096] chars
        - Exergy score > 0.3 required for admission
        - Train/val/test split (80/10/10) for MLX-LM
    """

    def __init__(
        self,
        workspace_path: str | Path,
        output_dir: str | Path | None = None,
        min_exergy: float = 0.3,
        seed: int = 42,
    ) -> None:
        self.workspace = Path(workspace_path)
        self.output_dir = Path(output_dir or Path.home() / ".babylon60" / "training" / "datasets")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[DatasetEntry] = []
        self.seen_hashes: set[str] = set()
        self.stats = CompilationStats()
        self.min_exergy = min_exergy
        self._rng = random.Random(seed)

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _filter_reason(self, reason: str) -> None:
        self.stats.filter_reasons[reason] = self.stats.filter_reasons.get(reason, 0) + 1
        self.stats.total_entries_filtered += 1

    def _add_entry(self, entry: DatasetEntry) -> bool:
        """Add entry with dedup, length bounds, and exergy check."""
        # Dedup
        content_hash = self._hash_content(f"{entry.instruction}{entry.output}")
        if content_hash in self.seen_hashes:
            self._filter_reason("duplicate")
            return False

        # Purge HTML comments and XML tags from instructions to prevent leakages
        entry.instruction = _HTML_COMMENT_RE.sub("", entry.instruction)
        entry.instruction = _SYSTEM_XML_TAGS_RE.sub("", entry.instruction).strip()

        # Length bounds
        inst_len = len(entry.instruction)
        output_len = len(entry.output.strip())
        
        if output_len < _MIN_OUTPUT_LENGTH:
            self._filter_reason("output_too_short")
            return False
        if inst_len < _MIN_INSTRUCTION_LENGTH:
            self._filter_reason("instruction_too_short")
            return False
        if inst_len > 1500:
            self._filter_reason("instruction_too_long")
            return False
        if (inst_len + output_len) > 3000:
            self._filter_reason("combined_length_exceeded")
            return False

        # Truncate oversized outputs
        entry.output = _truncate_output(entry.output)

        # Exergy scoring
        score = _exergy_score(entry.output)
        if score < self.min_exergy:
            self._filter_reason("low_exergy")
            return False
        entry.exergy_score = score

        entry.content_hash = content_hash
        self.seen_hashes.add(content_hash)
        self.entries.append(entry)
        self.stats.total_entries_generated += 1
        self.stats.categories[entry.category] = self.stats.categories.get(entry.category, 0) + 1
        return True

    # ─── Source Extractors ──────────────────────────────────────────────

    def extract_from_markdown_directives(self, file_path: Path) -> int:
        """Extract instruction pairs from structured markdown (AGENTS.md, GEMINI.md)."""
        if not file_path.exists():
            return 0

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to read markdown directive file %s: %s", file_path, e)
            return 0
        if len(content.strip()) < 100:
            logger.info("Skipping trivial markdown directive file: %s", file_path)
            return 0
        self.stats.total_files_scanned += 1
        self.stats.total_bytes_input += len(content.encode("utf-8"))

        # Strip HTML comments before parsing
        content = _HTML_COMMENT_RE.sub("", content)

        count = 0
        sections = re.split(r"\n## ", content)
        for section in sections:
            if not section.strip():
                continue
            lines = section.split("\n")
            title = lines[0].strip().lstrip("#").strip()

            # Skip empty/structural-only titles
            if not title or len(title) < 5 or title.startswith("─"):
                continue

            body = _clean_content("\n".join(lines[1:]))
            if len(body.strip()) < _MIN_OUTPUT_LENGTH:
                self._filter_reason("pre_short_directive")
                continue

            instruction = _pick_template(_DIRECTIVE_TEMPLATES, title=title)
            if self._add_entry(
                DatasetEntry(
                    instruction=instruction,
                    output=body.strip(),
                    category="directive",
                    source_file=str(file_path),
                )
            ):
                count += 1

        logger.info("Extracted %d entries from %s", count, file_path.name)
        return count

    def extract_from_skills(self, skills_dir: Path | None = None) -> int:
        """Extract instruction pairs from SKILL.md files."""
        search_dirs: list[Path] = []
        if skills_dir:
            search_dirs.append(skills_dir)
        search_dirs.extend(
            [
                self.workspace / ".agents" / "skills",
                Path.home() / ".gemini" / "config" / "skills",
            ]
        )

        count = 0
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for skill_md in sdir.rglob("SKILL.md"):
                try:
                    content = skill_md.read_text(encoding="utf-8")
                except Exception as e:  # noqa: BLE001
                    logger.warning("Failed to read skill file %s: %s", skill_md, e)
                    continue
                self.stats.total_files_scanned += 1
                self.stats.total_bytes_input += len(content.encode("utf-8"))

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
                if len(cleaned_body.strip()) < _MIN_OUTPUT_LENGTH:
                    self._filter_reason("pre_short_skill")
                    continue

                instruction = _pick_template(_SKILL_TEMPLATES, name=name, description=description)
                if self._add_entry(
                    DatasetEntry(
                        instruction=instruction,
                        output=cleaned_body.strip(),
                        category="skill",
                        source_file=str(skill_md),
                    )
                ):
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
            if any(
                skip in str(py_file) for skip in ["__pycache__", "test_", "migrations/", ".pyc"]
            ):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Failed to read Python file %s: %s", py_file, e)
                continue

            self.stats.total_files_scanned += 1
            self.stats.total_bytes_input += len(content.encode("utf-8"))

            # Extract module-level docstrings
            module_doc = self._extract_module_docstring(content)
            if module_doc and len(module_doc) > _MIN_OUTPUT_LENGTH:
                try:
                    rel_path = py_file.relative_to(self.workspace)
                except ValueError:
                    rel_path = py_file.name
                instruction = _pick_template(_CODE_MODULE_TEMPLATES, path=str(rel_path))
                if self._add_entry(
                    DatasetEntry(
                        instruction=instruction,
                        output=_clean_content(module_doc),
                        category="code_architecture",
                        source_file=str(py_file),
                    )
                ):
                    count += 1
            elif module_doc:
                self._filter_reason("pre_short_module_doc")

            # Extract class docstrings
            for class_name, class_doc in self._extract_class_docstrings(content):
                if len(class_doc) > _MIN_OUTPUT_LENGTH:
                    instruction = _pick_template(_CODE_CLASS_TEMPLATES, name=class_name)
                    if self._add_entry(
                        DatasetEntry(
                            instruction=instruction,
                            output=_clean_content(class_doc),
                            category="code_class",
                            source_file=str(py_file),
                        )
                    ):
                        count += 1
                else:
                    self._filter_reason("pre_short_class_doc")

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
        return ""

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
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Failed to read transcript file %s: %s", transcript_file, e)
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
                    # Clean user prompt: strip XML tags, HTML comments, metadata
                    cleaned_prompt = _clean_transcript_prompt(step_content)
                    # Skip system-injected or too-short prompts
                    if len(cleaned_prompt) >= _MIN_INSTRUCTION_LENGTH:
                        user_prompt = cleaned_prompt
                    else:
                        user_prompt = None
                elif step_type == "PLANNER_RESPONSE" and user_prompt and step_content:
                    cleaned = _clean_content(step_content)
                    # Only keep high-quality pairs with structured content
                    has_structure = (
                        "```" in cleaned
                        or "yaml" in cleaned.lower()
                        or "\n- " in cleaned
                        or "\n| " in cleaned
                    )
                    if len(cleaned) > 200 and has_structure:
                        if self._add_entry(
                            DatasetEntry(
                                instruction=user_prompt,
                                output=_truncate_output(cleaned),
                                category="session_transcript",
                                source_file=str(transcript_file),
                            )
                        ):
                            count += 1
                    user_prompt = None

        logger.info("Extracted %d entries from transcripts", count)
        return count

    def extract_from_memory_vault(self, vault_dir: Path | None = None) -> int:
        """Extract crystallized knowledge from Memory Vault files."""
        target = vault_dir or Path.home() / ".gemini" / "config" / ".cortex" / "memory_vault"
        if not target.exists():
            return 0

        count = 0
        for vault_file in target.iterdir():
            if vault_file.is_dir() or vault_file.name.startswith("."):
                continue

            try:
                content = vault_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Failed to read vault file %s: %s", vault_file, e)
                continue

            self.stats.total_files_scanned += 1
            self.stats.total_bytes_input += len(content.encode("utf-8"))

            cleaned = _clean_content(content)
            if len(cleaned.strip()) < _MIN_OUTPUT_LENGTH:
                self._filter_reason("pre_short_vault")
                continue

            # Derive title from filename
            title = vault_file.stem.replace("_", " ").replace("-", " ").title()

            instruction = _pick_template(_VAULT_TEMPLATES, title=title)
            if self._add_entry(
                DatasetEntry(
                    instruction=instruction,
                    output=_truncate_output(cleaned),
                    category="memory_vault",
                    source_file=str(vault_file),
                )
            ):
                count += 1

        logger.info("Extracted %d entries from Memory Vault", count)
        return count

    def extract_from_workflows(self, workflows_dir: Path | None = None) -> int:
        """Extract workflow protocols from .agents/workflows/."""
        target = workflows_dir or self.workspace / ".agents" / "workflows"
        if not target.exists():
            return 0

        count = 0
        for wf_file in target.glob("*.md"):
            try:
                content = wf_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Failed to read workflow file %s: %s", wf_file, e)
                continue

            self.stats.total_files_scanned += 1
            self.stats.total_bytes_input += len(content.encode("utf-8"))

            # Parse frontmatter/first line for description
            name = wf_file.stem.replace("-", " ").replace("_", " ").title()
            description = ""

            # Try to extract description from first header or line
            lines = content.split("\n")
            for line in lines[:10]:
                stripped = line.strip().lstrip("#").strip()
                if stripped and len(stripped) > 10 and not stripped.startswith("---"):
                    description = stripped
                    break

            cleaned = _clean_content(content)
            if len(cleaned.strip()) < _MIN_OUTPUT_LENGTH:
                self._filter_reason("pre_short_workflow")
                continue

            instruction = _pick_template(
                _WORKFLOW_TEMPLATES,
                name=name,
                description=description or "protocolo de ejecución",
            )
            if self._add_entry(
                DatasetEntry(
                    instruction=instruction,
                    output=_truncate_output(cleaned),
                    category="workflow",
                    source_file=str(wf_file),
                )
            ):
                count += 1

        logger.info("Extracted %d entries from workflows", count)
        return count

    def extract_from_ledger_db(self, db_path: str | Path | None = None) -> int:
        """Extract high-value facts from the CORTEX SQLite database."""
        if db_path is None:
            # Try common DB locations
            candidates = [
                Path.home() / ".cortex" / "cortex.db",
                Path(os.getenv("CORTEX_DB_PATH", "")),
                self.workspace / "cortex.db",
            ]
            db_path_resolved = None
            for c in candidates:
                if c.exists():
                    db_path_resolved = c
                    break
            if db_path_resolved is None:
                logger.debug("No CORTEX DB found, skipping ledger extraction")
                return 0
        else:
            db_path_resolved = Path(db_path)

        count = 0
        try:
            # R10 Compliance: Rigid busy_timeout (5000ms) and WAL mode active
            conn = sqlite3.connect(str(db_path_resolved), timeout=5.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row

            # Extract high-confidence facts
            cursor = conn.execute(
                """
                SELECT content, project, fact_type, confidence, source, tags
                FROM facts
                WHERE confidence IN ('verified', 'high', 'axiom')
                  AND content IS NOT NULL
                  AND LENGTH(content) > 100
                  AND valid_until IS NULL
                ORDER BY created_at DESC
                LIMIT 500
                """
            )

            for row in cursor:
                row_dict = dict(row)
                content = row_dict.get("content")
                if not content:
                    continue
                fact_type = row_dict.get("fact_type") or "general"
                project = row_dict.get("project") or "cortex"
                tags = row_dict.get("tags") or ""

                instruction = (
                    f"Recupera el hecho verificado de tipo '{fact_type}' del proyecto '{project}'"
                )
                if tags:
                    instruction += f" (tags: {tags})"

                if self._add_entry(
                    DatasetEntry(
                        instruction=instruction,
                        output=_truncate_output(_clean_content(content)),
                        category="ledger_fact",
                        source_file=str(db_path_resolved),
                    )
                ):
                    count += 1

            conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.warning("Ledger DB extraction failed: %s", e)

        logger.info("Extracted %d entries from Ledger DB", count)
        return count

    # ─── Compilation Pipeline ──────────────────────────────────────────

    def compile_full_dataset(self) -> CompilationStats:
        """Execute the full compilation pipeline across all sources."""
        logger.info("🔧 MOSKV-1 Dataset Compilation v2.0 — Starting...")

        # 1. Axioms & Directives
        self.extract_from_markdown_directives(self.workspace / "AGENTS.md")
        self.extract_from_markdown_directives(self.workspace / "GEMINI.md")

        # 2. Skills
        self.extract_from_skills()

        # 3. Python module architecture
        self.extract_from_python_modules()

        # 4. Session transcripts
        self.extract_from_transcripts()

        # 5. Memory Vault (NEW v2.0)
        self.extract_from_memory_vault()

        # 6. Workflows (NEW v2.0)
        self.extract_from_workflows()

        # 7. Ledger DB facts (NEW v2.0)
        self.extract_from_ledger_db()

        # Calculate output bytes and avg exergy
        total_exergy = 0.0
        for entry in self.entries:
            self.stats.total_bytes_output += len(
                json.dumps(entry.to_sharegpt(), ensure_ascii=False).encode("utf-8")
            )
            total_exergy += entry.exergy_score

        if self.entries:
            self.stats.avg_exergy_score = total_exergy / len(self.entries)

        # Sort by exergy score (highest quality first)
        self.entries.sort(key=lambda e: e.exergy_score, reverse=True)

        logger.info(
            "🔧 Compilation complete: %d entries, %.1f%% yield, "
            "%.2f avg exergy, %.1f%% compression",
            self.stats.total_entries_generated,
            self.stats.exergy_yield * 100,
            self.stats.avg_exergy_score,
            self.stats.compression_ratio * 100,
        )
        return self.stats

    def _split_dataset(
        self,
        entries: list[DatasetEntry],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
    ) -> tuple[list[DatasetEntry], list[DatasetEntry], list[DatasetEntry]]:
        """Split entries into train/val/test sets (shuffled, deterministic)."""
        shuffled = list(entries)
        self._rng.shuffle(shuffled)

        n = len(shuffled)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]

    def export_sharegpt(
        self,
        filename: str = "moskv1_dataset.jsonl",
        split: bool = True,
    ) -> Path:
        """Export dataset in ShareGPT JSONL format (MLX-LM compatible)."""
        if split:
            train, val, test = self._split_dataset(self.entries)
            for name, subset in [("train", train), ("valid", val), ("test", test)]:
                path = self.output_dir / f"{name}.jsonl"
                with open(path, "w", encoding="utf-8") as f:
                    for entry in subset:
                        f.write(json.dumps(entry.to_sharegpt(), ensure_ascii=False) + "\n")
                logger.info("💾 %s: %d entries → %s", name, len(subset), path)

        # Also export combined
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(json.dumps(entry.to_sharegpt(), ensure_ascii=False) + "\n")

        logger.info(
            "💾 Exported %d entries to %s (split=%s)", len(self.entries), output_path, split
        )
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
        filter_lines = "\n".join(
            f"  {reason}: {count}" for reason, count in sorted(self.stats.filter_reasons.items())
        )
        return (
            f"total_files_scanned: {self.stats.total_files_scanned}\n"
            f"total_entries_generated: {self.stats.total_entries_generated}\n"
            f"total_entries_filtered: {self.stats.total_entries_filtered}\n"
            f"exergy_yield: {self.stats.exergy_yield:.2%}\n"
            f"avg_exergy_score: {self.stats.avg_exergy_score:.3f}\n"
            f"compression_ratio: {self.stats.compression_ratio:.2%}\n"
            f"categories:\n"
            + "\n".join(f"  {cat}: {count}" for cat, count in sorted(self.stats.categories.items()))
            + "\nfilter_reasons:\n"
            + (filter_lines or "  none: 0")
        )
