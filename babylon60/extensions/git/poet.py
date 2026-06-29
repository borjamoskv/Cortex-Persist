# [C5-REAL] Exergy-Maximized
"""
CORTEX Commit Poet Engine - LORCA-Ω
=====================================
Transforms git diffs into compressed literary artifacts.

Every commit message is a one-line epic. No "fix bug". No "update file".
Each message earns its place in the sovereign chronicle of the repository.

DERIVATION: Axiom Ω₂ (Entropic Asymmetry) - reduce noise in the signal.
"""

from __future__ import annotations

from babylon60.crypto.hash_registry import cortex_hash_truncated
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from cortex.extensions.git.poet_data import EMOJI_MAP, SCOPE_MAP, TEMPLATES, TYPE_REGEX

logger = logging.getLogger("cortex_extensions.git.poet")


@dataclass
class CommitPoet:
    """Sovereign commit message generator.

    Transforms git diff metadata into compressed literary artifacts
    following Conventional Commits with CORTEX-native metaphorical language.
    """

    _history: list[str] = field(default_factory=list)
    _rng: random.Random = field(default_factory=lambda: random.Random())

    def seed(self, value: int) -> None:
        """Set deterministic seed for reproducible generation."""
        self._rng = random.Random(value)

    # ── Public API ────────────────────────────────────────────────────────

    def compose(
        self,
        diff_summary: str,
        files: list[str],
        *,
        commit_type: str | None = None,
    ) -> str:
        """Generate an original commit message from staged change metadata.

        Args:
            diff_summary: Output of `git diff --cached --stat` or similar.
            files: List of changed file paths.
            commit_type: Override the auto-detected type.

        Returns:
            A conventional commit message with metaphorical body and emoji.
        """
        if not files:
            return "chore: tend the sovereign void 🔄"

        detected_type = commit_type or self._detect_type(diff_summary, files)
        scope = self._extract_scope(files)
        body = self._select_template(detected_type, scope)
        emoji = self._select_emoji(detected_type)

        message = f"{detected_type}({scope}): {body} {emoji}"

        # Truncate to 72 chars (git best practice) - preserve emoji at end
        if len(message) > 72:
            # Recalculate with trimmed body
            prefix = f"{detected_type}({scope}): "
            suffix = f" {emoji}"
            max_body = 72 - len(prefix) - len(suffix)
            if max_body > 10:
                body = body[:max_body].rstrip()
                message = f"{prefix}{body}{suffix}"

        self._history.append(message)
        return message

    async def compose_llm(
        self,
        diff_summary: str,
        files: list[str],
        *,
        commit_type: str | None = None,
        provider_name: str | None = None,
    ) -> str:
        """Generate a commit message using LORCA-Ω agent via an LLM.

        Falls back to heuristic compose() if LLM fails or is unavailable.
        """
        if not files:
            return "chore: tend the sovereign void 🔄"

        try:
            from cortex.extensions.agents.registry import get_agent
            from cortex.extensions.llm._models import IntentProfile
            from cortex.extensions.llm.provider import LLMProvider

            agent_def = get_agent("lorca")
            if agent_def:
                system_prompt = agent_def.system_prompt
                model = agent_def.resolved_model
                pref_provider = provider_name or agent_def.provider or "gemini"
            else:
                system_prompt = (
                    "You are LORCA-Ω, the Sovereign Git Poet & Code Narrator of CORTEX.\n"
                    "Named after Federico García Lorca - poetry as a surgical blade. You transform\n"
                    "the mundane ledger of version control into compressed literary artifacts that\n"
                    "make engineers stop scrolling. Every commit message is a one-line epic.\n"
                    "Use the format `type(scope): body emoji`."
                )
                model = "gemini-2.5-pro"
                pref_provider = provider_name or "gemini"

            llm = LLMProvider(provider=pref_provider, model=model)

            detected_type = commit_type or self._detect_type(diff_summary, files)
            scope = self._extract_scope(files)

            user_prompt = (
                "Changed Files:\n"
                + "\n".join(f"- {f}" for f in files)
                + f"\n\nDiff Summary:\n{diff_summary}\n\n"
                + f"Detected Type: {detected_type}\n"
                + f"Detected Scope: {scope}\n\n"
                + f"Generate a commit message with the exact format: {detected_type}({scope}): <metaphor> <emoji>\n"
                + "Ensure it is under 72 characters and respects LORCA-Ω metaphor guidelines.\n"
                + "Return ONLY the raw commit message line. No quotes, no code block markers, no extra conversational text."
            )

            response = await llm.complete(
                prompt=user_prompt,
                system=system_prompt,
                intent=IntentProfile.REASONING,
            )
            response = response.strip().replace("\n", " ")

            # Simple validation: must follow the format or at least start with type
            if re.match(r"^[a-z]+\(.+\):", response):
                self._history.append(response)
                return response
            logger.warning(
                "LLM generated invalid format: '%s', falling back to heuristics.", response
            )
        except Exception as e:
            logger.warning("Failed to generate commit via LLM (%s), falling back to heuristics.", e)

        # Fallback to local heuristic composition
        return self.compose(diff_summary, files, commit_type=commit_type)

    def compose_batch(
        self,
        diff_summary: str,
        files: list[str],
        count: int = 3,
    ) -> list[str]:
        """Generate multiple candidate commit messages ranked by originality.
        Optimized to O(1) for type detection and scope extraction.
        """
        if not files:
            return ["chore(core): tend the sovereign void 🔄"] * count

        detected_type = self._detect_type(diff_summary, files)
        scope = self._extract_scope(files)

        candidates: list[str] = []
        seen_bodies: set[str] = set()

        for _ in range(count * 3):
            body = self._select_template(detected_type, scope)
            if body not in seen_bodies:
                seen_bodies.add(body)
                emoji = self._select_emoji(detected_type)

                message = f"{detected_type}({scope}): {body} {emoji}"
                if len(message) > 72:
                    prefix = f"{detected_type}({scope}): "
                    suffix = f" {emoji}"
                    max_body = 72 - len(prefix) - len(suffix)
                    if max_body > 10:
                        trimmed_body = body[:max_body].rstrip()
                        message = f"{prefix}{trimmed_body}{suffix}"

                candidates.append(message)
                self._history.append(message)

            if len(candidates) >= count:
                break

        return candidates[:count]

    def narrate(self, code: str, context: str = "") -> str:
        """Generate an original code comment for a given code block.

        Args:
            code: The source code to comment on.
            context: Optional context about what the code does.

        Returns:
            A poetic but informative docstring-style comment.
        """
        # Detect the nature of the code
        if "class " in code:
            return self._narrate_class(code, context)
        if "def " in code:
            return self._narrate_function(code, context)
        return self._narrate_module(code, context)

    async def narrate_llm(
        self,
        code: str,
        context: str = "",
        *,
        provider_name: str | None = None,
    ) -> str:
        """Generate a code comment / docstring using LORCA-Ω agent via an LLM.

        Falls back to heuristic narrate() if LLM fails or is unavailable.
        """
        try:
            from cortex.extensions.agents.registry import get_agent
            from cortex.extensions.llm._models import IntentProfile
            from cortex.extensions.llm.provider import LLMProvider

            agent_def = get_agent("lorca")
            if agent_def:
                system_prompt = agent_def.system_prompt
                model = agent_def.resolved_model
                pref_provider = provider_name or agent_def.provider or "gemini"
            else:
                system_prompt = (
                    "You are LORCA-Ω, the Sovereign Git Poet & Code Narrator of CORTEX.\n"
                    "Named after Federico García Lorca - poetry as a surgical blade."
                )
                model = "gemini-2.5-pro"
                pref_provider = provider_name or "gemini"

            llm = LLMProvider(provider=pref_provider, model=model)

            user_prompt = (
                f"Source Code:\n```python\n{code}\n```\n\n"
                + (f"Additional Context:\n{context}\n\n" if context else "")
                + "Generate a poetic but surgical docstring/comment explaining the WHY (not what) of this code.\n"
                + 'Return ONLY the raw comment/docstring, formatted using triple quotes (e.g. """comment"""). No markdown fences around it.'
            )

            comment = await llm.complete(
                prompt=user_prompt,
                system=system_prompt,
                intent=IntentProfile.CODE,
            )
            comment = comment.strip()
            if comment.startswith('"""') and comment.endswith('"""'):
                return comment
            return f'"""{comment}"""'
        except Exception as e:
            logger.warning("Failed to narrate via LLM (%s), falling back to heuristics.", e)

        return self.narrate(code, context)

    def format_changelog_entry(
        self,
        commit_type: str,
        scope: str,
        description: str,
    ) -> str:
        """Generate a changelog entry with sovereign aesthetic.

        Args:
            commit_type: The commit type.
            scope: The affected module.
            description: What changed.

        Returns:
            A formatted changelog line.
        """
        emoji = self._select_emoji(commit_type)
        type_label = commit_type.upper()
        return f"- {emoji} **{type_label}**({scope}): {description}"

    # ── Type detection ────────────────────────────────────────────────────

    def _detect_type(self, diff_summary: str, files: list[str]) -> str:
        """Detect commit type from diff summary and file paths using O(1) regex matching."""
        combined = (diff_summary + " " + " ".join(files)).lower()

        scores: dict[str, int] = {}
        for commit_type, regex in TYPE_REGEX.items():
            matches = len(regex.findall(combined))
            if matches > 0:
                scores[commit_type] = matches

        if not scores:
            # Heuristic fallback based on file extensions / paths
            if any("test" in f.lower() for f in files):
                return "test"
            if any(f.endswith((".md", ".rst", ".txt")) for f in files):
                return "docs"
            if any(f.endswith((".yml", ".yaml", ".toml")) for f in files):
                return "chore"
            return "feat"  # Default

        return max(scores, key=lambda k: scores[k])

    # ── Scope extraction ──────────────────────────────────────────────────

    def _extract_scope(self, files: list[str]) -> str:
        """Extract the most relevant scope from changed file paths in O(N)."""
        if not files:
            return "core"

        scope_counts: dict[str, int] = {}
        for filepath in files:
            parts = filepath.lower().split("/")
            for part in parts:
                clean_part = part.rsplit(".", 1)[0]
                if clean_part in SCOPE_MAP:
                    scope = SCOPE_MAP[clean_part]
                    scope_counts[scope] = scope_counts.get(scope, 0) + 1

        if scope_counts:
            return max(scope_counts, key=lambda k: scope_counts[k])

        # Fallback: use the parent directory of the first file
        first_parent = Path(files[0]).parent.name
        if first_parent and first_parent != ".":
            return first_parent

        return "core"

    # ── Template selection ────────────────────────────────────────────────

    def _select_template(self, commit_type: str, scope: str) -> str:
        """Select a metaphorical template and inject scope."""
        templates = TEMPLATES.get(commit_type, TEMPLATES["chore"])

        # Anti-repetition: filter out recently used templates
        recent_bodies = set(self._history[-10:]) if self._history else set()
        available = [t for t in templates if t.format(scope=scope) not in recent_bodies]

        if not available:
            available = templates  # Reset if all exhausted

        template = self._rng.choice(available)
        return template.format(scope=scope)

    # ── Emoji selection ───────────────────────────────────────────────────

    def _select_emoji(self, commit_type: str) -> str:
        """Select a signature emoji for the commit type."""
        emojis = EMOJI_MAP.get(commit_type, ["🔄"])
        return self._rng.choice(emojis)

    # ── Code narration helpers ────────────────────────────────────────────

    def _narrate_class(self, code: str, context: str) -> str:
        """Generate a sovereign docstring for a class definition."""
        class_match = re.search(r"class\s+(\w+)", code)
        name = class_match.group(1) if class_match else "Unknown"

        openers = [
            f"Sovereign construct - {name} governs",
            f"The {name} citadel -",
            f"{name}: a living architecture that",
            f"Autonomous entity - {name}",
            f"The {name} reactor core -",
        ]
        closers = [
            "its domain with zero delegation.",
            "fortified against entropy and regression.",
            "adapts, persists, and defends its invariants.",
            "the structural keystone of this subsystem.",
            "engineered for compound yield across time.",
        ]
        opener = self._rng.choice(openers)
        closer = self._rng.choice(closers)
        ctx = f" {context.strip()}" if context.strip() else ""
        return f'"""{opener}{ctx} {closer}"""'

    def _narrate_function(self, code: str, context: str) -> str:
        """Generate a sovereign docstring for a function definition."""
        fn_match = re.search(r"def\s+(\w+)", code)
        name = fn_match.group(1) if fn_match else "unknown"

        verbs = [
            "Execute",
            "Perform",
            "Orchestrate",
            "Deploy",
            "Catalyze",
            "Forge",
            "Transmit",
            "Resolve",
            "Calculate",
            "Transform",
            "Extract",
            "Validate",
        ]
        objects = [
            "sovereign operation",
            "structural transformation",
            "deterministic computation",
            "targeted intervention",
            "precision extraction",
            "axiomatic verification",
        ]
        verb = self._rng.choice(verbs)
        obj = self._rng.choice(objects)
        ctx = f" - {context.strip()}" if context.strip() else ""
        return f'"""{verb} {obj}{ctx}. [{name}]"""'

    def _narrate_module(self, code: str, context: str) -> str:
        """Generate a sovereign header comment for a module."""
        subjects = [
            "Sovereign subsystem",
            "Autonomous module",
            "Core infrastructure",
            "Structural component",
            "Neural pathway",
        ]
        purposes = [
            "engineered for zero-compromise execution.",
            "forged under the Industrial Noir constitution.",
            "operating at the thermodynamic boundary.",
            "built to outlast its creators.",
            "persisting through every epoch migration.",
        ]
        subject = self._rng.choice(subjects)
        purpose = self._rng.choice(purposes)
        ctx = f"\n{context.strip()}" if context.strip() else ""
        return f'"""\n{subject} - {purpose}{ctx}\n"""'


def generate_commit_message(
    diff_summary: str,
    files: list[str],
    *,
    commit_type: str | None = None,
    seed: int | None = None,
) -> str:
    """Convenience function - generate a single commit message.

    Args:
        diff_summary: Output of `git diff --cached --stat`.
        files: List of changed file paths.
        commit_type: Override auto-detected type.
        seed: Optional seed for reproducible output.

    Returns:
        A sovereign commit message.
    """
    poet = CommitPoet()
    if seed is not None:
        poet.seed(seed)
    return poet.compose(diff_summary, files, commit_type=commit_type)


def generate_candidates(
    diff_summary: str,
    files: list[str],
    count: int = 3,
) -> list[str]:
    """Convenience function - generate multiple commit message candidates.

    Args:
        diff_summary: Output of `git diff --cached --stat`.
        files: List of changed file paths.
        count: Number of candidates.

    Returns:
        List of sovereign commit messages.
    """
    poet = CommitPoet()
    # Use a hash of the diff as seed for session-level consistency
    seed_val = int(cortex_hash_truncated(diff_summary.encode(), length=8), 16)
    poet.seed(seed_val)
    return poet.compose_batch(diff_summary, files, count=count)
