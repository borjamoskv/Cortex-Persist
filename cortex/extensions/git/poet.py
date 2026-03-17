"""
CORTEX Commit Poet Engine — LORCA-Ω
=====================================
Transforms git diffs into compressed literary artifacts.

Every commit message is a one-line epic. No "fix bug". No "update file".
Each message earns its place in the sovereign chronicle of the repository.

DERIVATION: Axiom Ω₂ (Entropic Asymmetry) — reduce noise in the signal.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Commit type detection heuristics ──────────────────────────────────────────

_TYPE_SIGNALS: dict[str, list[str]] = {
    "feat": ["new file", "added", "create", "implement", "introduce", "add"],
    "fix": ["fix", "bug", "error", "crash", "patch", "repair", "resolve"],
    "refactor": ["rename", "move", "restructure", "reorganize", "extract", "simplify"],
    "perf": ["optimize", "cache", "speed", "latency", "benchmark", "fast"],
    "docs": ["readme", "doc", "comment", "changelog", "license", "manifest"],
    "test": ["test", "spec", "assert", "mock", "fixture", "coverage"],
    "ci": ["ci", "github", "workflow", "pipeline", "deploy", "docker"],
    "style": ["lint", "format", "whitespace", "indent", "ruff", "pyright"],
    "chore": ["bump", "update", "upgrade", "dependency", "cleanup", "misc"],
}

# ── Metaphorical templates per commit type ────────────────────────────────────
# Each template is a format string. `{scope}` is injected at compose time.

_TEMPLATES: dict[str, list[str]] = {
    "feat": [
        "ignite the {scope} reactor",
        "forge {scope} from the sovereign anvil",
        "crystallize {scope} into existence",
        "birth the {scope} neural pathway",
        "weave {scope} into the living membrane",
        "conjure {scope} from the thermodynamic void",
        "plant the {scope} seed in the sovereign garden",
        "give {scope} its first heartbeat",
        "awaken {scope} from the dormant lattice",
        "mint {scope} on the sovereign ledger",
        "carve {scope} into the bedrock",
        "distill {scope} from raw entropy",
        "unfurl the {scope} constellation",
        "lay the {scope} keystone",
        "inject {scope} into the bloodstream",
        "spark the {scope} ignition sequence",
        "graft {scope} onto the living architecture",
        "cast {scope} in sovereign alloy",
        "encode {scope} into the double helix",
        "terraform {scope} for habitation",
        "architect the {scope} cantilever",
        "nucleate {scope} in the supersaturated solution",
        "bootstrap {scope} from first principles",
        "deploy the {scope} vanguard",
        "summon {scope} through the event horizon",
    ],
    "fix": [
        "cauterize the wound in {scope}",
        "exorcise the ghost haunting {scope}",
        "suture the breach in {scope}",
        "neutralize the pathogen in {scope}",
        "seal the entropy leak in {scope}",
        "realign the fractured {scope} axis",
        "purge the toxic residue from {scope}",
        "restore the broken symmetry of {scope}",
        "mend the torn fabric of {scope}",
        "extinguish the cascade failure in {scope}",
        "inoculate {scope} against regression",
        "quench the thermal runaway in {scope}",
        "stabilize the {scope} orbit decay",
        "drain the abscess from {scope}",
        "rethread the severed {scope} nerve",
        "annihilate the phantom signal in {scope}",
        "close the gravitational wound in {scope}",
        "extract the embedded shrapnel from {scope}",
        "recalibrate the {scope} drift correction",
        "defuse the silent detonator in {scope}",
    ],
    "refactor": [
        "metamorphose {scope} to its sovereign form",
        "annihilate entropy accumulated in {scope}",
        "purify the {scope} signal",
        "distill {scope} to its irreducible essence",
        "transmute the {scope} lead into gold",
        "strip {scope} to the structural bone",
        "reforge {scope} in the crucible",
        "compress the {scope} wavefunction",
        "untangle the {scope} gordian knot",
        "temper {scope} through sovereign heat treatment",
        "sculpt {scope} with subtractive precision",
        "realign {scope} along the geodesic",
        "collapse the {scope} redundancy manifold",
        "anoint {scope} with O(1) clarity",
        "shed the vestigial exoskeleton of {scope}",
        "elevate {scope} from clay to marble",
        "decouple the {scope} gravitational binding",
        "crystallize {scope} into its final polymorph",
        "extract the {scope} signal from thermal noise",
        "prune the {scope} dead branches",
    ],
    "perf": [
        "accelerate {scope} beyond escape velocity",
        "compress spacetime in the {scope} pipeline",
        "shatter the {scope} latency barrier",
        "overclock the {scope} throughput reactor",
        "eliminate the {scope} friction coefficient",
        "superconduct the {scope} critical path",
        "collapse the {scope} computational manifold",
        "inject nitrous into the {scope} engine",
        "achieve {scope} terminal velocity",
        "liquefy the {scope} bottleneck",
        "tune {scope} to resonant frequency",
        "strip aerodynamic drag from {scope}",
        "unlock the {scope} warp drive",
        "anneal {scope} for zero-resistance flow",
        "vaporize the {scope} memory overhead",
    ],
    "docs": [
        "inscribe the scripture of {scope}",
        "illuminate the dark matter of {scope}",
        "chart the {scope} territory for future navigators",
        "engrave {scope} wisdom into the stone tablet",
        "decode the {scope} rosetta stone",
        "author the {scope} survival manual",
        "map the {scope} cartography for the swarm",
        "chronicle the {scope} epoch transition",
        "translate {scope} from machine to human",
        "annotate the {scope} archaeological record",
        "index the {scope} sovereign knowledge base",
        "publish the {scope} field reconnaissance",
    ],
    "test": [
        "deploy the verification membrane around {scope}",
        "probe the structural integrity of {scope}",
        "fire the {scope} stress test barrage",
        "inoculate {scope} with regression antibodies",
        "construct the {scope} byzantine fault detector",
        "erect the {scope} perimeter defense grid",
        "simulate {scope} under adversarial conditions",
        "calibrate the {scope} truth oracle",
        "arm the {scope} tripwire network",
        "subject {scope} to sovereign audit",
        "validate the {scope} invariant fortress",
        "deploy chaos probes against {scope}",
    ],
    "ci": [
        "wire the {scope} deployment pipeline",
        "automate the {scope} launch sequence",
        "install the {scope} continuous forge",
        "activate the {scope} autonomous build reactor",
        "harden the {scope} delivery corridor",
        "establish the {scope} sovereign supply chain",
        "provision the {scope} orbital deployment",
        "arm the {scope} release catapult",
    ],
    "style": [
        "polish the {scope} sovereign surface",
        "align the {scope} crystalline lattice",
        "discipline the {scope} visual rhythm",
        "harmonize the {scope} typographic frequency",
        "enforce the {scope} aesthetic constitution",
        "calibrate the {scope} formatting resonance",
    ],
    "chore": [
        "maintain the {scope} sovereign substrate",
        "renew the {scope} cosmic infrastructure",
        "tend the {scope} orbital machinery",
        "recycle the {scope} thermal waste",
        "service the {scope} autonomous systems",
        "lubricate the {scope} kinetic bearings",
        "rotate the {scope} cryptographic seals",
        "restock the {scope} supply depot",
    ],
    "revert": [
        "reverse the {scope} temporal anomaly",
        "undo the {scope} spacetime distortion",
        "roll back the {scope} failed mutation",
        "recall the {scope} defective deployment",
    ],
}

# ── Emoji signatures per commit type ──────────────────────────────────────────

_EMOJI_MAP: dict[str, list[str]] = {
    "feat": ["⚡", "🧬", "🔮", "🌱", "🏗️", "💎", "🚀", "🔥", "✨", "🧊"],
    "fix": ["🩹", "🔧", "🛡️", "💉", "🩺", "⚕️", "🔒", "🧯", "🪡", "🗡️"],
    "refactor": ["♻️", "🔬", "⚗️", "🪨", "🧹", "🌀", "🔭", "🪞", "🫧", "🧱"],
    "perf": ["⚡", "🏎️", "💨", "🔋", "⏱️", "🦅", "🌊", "🧲", "🔩", "🛸"],
    "docs": ["📜", "🗺️", "📡", "🔍", "📖", "🧭", "📐", "🏛️", "📋", "🪶"],
    "test": ["🧪", "🛡️", "🎯", "🔬", "🧫", "🏹", "⚔️", "🪤", "🔎", "🧿"],
    "ci": ["🏭", "🤖", "⚙️", "🔗", "🛰️", "📦", "🧰", "🪝"],
    "style": ["🎨", "💅", "📏", "✏️", "🖋️", "🔲"],
    "chore": ["🔄", "🧹", "🛠️", "📎", "🗂️", "🪛", "⛽", "🧴"],
    "revert": ["⏪", "🔙", "↩️", "🕐"],
}

# ── Scope extraction from file paths ─────────────────────────────────────────

_SCOPE_MAP: dict[str, str] = {
    "engine": "engine",
    "memory": "memory",
    "search": "search",
    "graph": "graph",
    "cli": "cli",
    "api": "api",
    "routes": "routes",
    "mcp": "mcp",
    "auth": "auth",
    "crypto": "crypto",
    "security": "security",
    "guards": "guards",
    "audit": "audit",
    "ledger": "ledger",
    "embeddings": "embeddings",
    "llm": "llm",
    "agents": "agents",
    "swarm": "swarm",
    "tests": "tests",
    "daemon": "daemon",
    "config": "config",
    "migrate": "migrations",
    "notifications": "notifications",
    "telemetry": "telemetry",
    "evolution": "evolution",
    "axioms": "axioms",
    "skills": "skills",
    "immune": "immune",
    "consensus": "consensus",
    "git": "git",
    "web": "web",
    "docs": "docs",
    "scripts": "scripts",
    "compaction": "compaction",
    "context": "context",
    "storage": "storage",
    "database": "database",
    "sync": "sync",
    "hive": "hive",
    "alma": "alma",
    "thinking": "thinking",
    "perception": "perception",
    "platform": "platform",
    "signals": "signals",
    "events": "events",
    "sovereign": "sovereign",
    "hypervisor": "hypervisor",
}


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
        commit_type: Optional[str] = None,
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

        # Truncate to 72 chars (git best practice) — preserve emoji at end
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

    def compose_batch(
        self,
        diff_summary: str,
        files: list[str],
        count: int = 3,
    ) -> list[str]:
        """Generate multiple candidate commit messages ranked by originality.

        Args:
            diff_summary: Output of `git diff --cached --stat`.
            files: List of changed file paths.
            count: Number of candidates to generate.

        Returns:
            List of commit messages sorted by information density.
        """
        candidates: list[str] = []
        seen_bodies: set[str] = set()

        for _ in range(count * 3):  # Over-generate to filter duplicates
            msg = self.compose(diff_summary, files)
            # Extract body for dedup
            body_match = re.search(r":\s+(.+?)\s+\S+$", msg)
            body = body_match.group(1) if body_match else msg
            if body not in seen_bodies:
                seen_bodies.add(body)
                candidates.append(msg)
            # Pop from history to allow re-generation
            if self._history:
                self._history.pop()
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
        """Detect commit type from diff summary and file paths."""
        combined = (diff_summary + " " + " ".join(files)).lower()

        scores: dict[str, int] = {}
        for commit_type, signals in _TYPE_SIGNALS.items():
            score = sum(1 for signal in signals if signal in combined)
            if score > 0:
                scores[commit_type] = score

        if not scores:
            # Heuristic fallback based on file extensions / paths
            if any("test" in f.lower() for f in files):
                return "test"
            if any(f.endswith((".md", ".rst", ".txt")) for f in files):
                return "docs"
            if any(f.endswith((".yml", ".yaml", ".toml")) for f in files):
                return "chore"
            return "feat"  # Default — creation is the default state

        return max(scores, key=lambda k: scores[k])

    # ── Scope extraction ──────────────────────────────────────────────────

    def _extract_scope(self, files: list[str]) -> str:
        """Extract the most relevant scope from changed file paths."""
        scope_counts: dict[str, int] = {}

        for filepath in files:
            parts = Path(filepath).parts
            for part in parts:
                part_lower = part.lower().rstrip(".py").rstrip(".yaml").rstrip(".yml")
                if part_lower in _SCOPE_MAP:
                    scope = _SCOPE_MAP[part_lower]
                    scope_counts[scope] = scope_counts.get(scope, 0) + 1

        if scope_counts:
            return max(scope_counts, key=lambda k: scope_counts[k])

        # Fallback: use the parent directory of the first file
        if files:
            first_parent = Path(files[0]).parent.name
            if first_parent and first_parent != ".":
                return first_parent

        return "core"

    # ── Template selection ────────────────────────────────────────────────

    def _select_template(self, commit_type: str, scope: str) -> str:
        """Select a metaphorical template and inject scope."""
        templates = _TEMPLATES.get(commit_type, _TEMPLATES["chore"])

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
        emojis = _EMOJI_MAP.get(commit_type, ["🔄"])
        return self._rng.choice(emojis)

    # ── Code narration helpers ────────────────────────────────────────────

    def _narrate_class(self, code: str, context: str) -> str:
        """Generate a sovereign docstring for a class definition."""
        class_match = re.search(r"class\s+(\w+)", code)
        name = class_match.group(1) if class_match else "Unknown"

        openers = [
            f"Sovereign construct — {name} governs",
            f"The {name} citadel —",
            f"{name}: a living architecture that",
            f"Autonomous entity — {name}",
            f"The {name} reactor core —",
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
        ]
        verb = self._rng.choice(verbs)
        obj = self._rng.choice(objects)
        ctx = f" — {context.strip()}" if context.strip() else ""
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
        return f'"""\n{subject} — {purpose}{ctx}\n"""'


def generate_commit_message(
    diff_summary: str,
    files: list[str],
    *,
    commit_type: Optional[str] = None,
    seed: Optional[int] = None,
) -> str:
    """Convenience function — generate a single commit message.

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
    """Convenience function — generate multiple commit message candidates.

    Args:
        diff_summary: Output of `git diff --cached --stat`.
        files: List of changed file paths.
        count: Number of candidates.

    Returns:
        List of sovereign commit messages.
    """
    poet = CommitPoet()
    # Use a hash of the diff as seed for session-level consistency
    seed_val = int(hashlib.md5(diff_summary.encode()).hexdigest()[:8], 16)
    poet.seed(seed_val)
    return poet.compose_batch(diff_summary, files, count=count)
