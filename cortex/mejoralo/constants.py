"""Constants for MEJORAlo engine."""

import re

__all__ = [
    "DAEMON_DEFAULT_SCAN_INTERVAL",
    "DAEMON_DEFAULT_TARGET_SCORE",
    "DAEMON_DIM_SCORE_THRESHOLD",
    "DEVILS_ADVOCATE_THRESHOLD",
    "ESCALATION_ITER_L2",
    "ESCALATION_ITER_L3",
    "FILES_PER_ITERATION",
    "HARD_ITERATION_CAP",
    "HEAL_TEMPERATURES",
    "INDENT_NESTING_THRESHOLD",
    "INMEJORABLE_SCORE",
    "MAX_FAN_OUT",
    "MAX_FINDINGS_ARCH",
    "MAX_FINDINGS_COMPLEXITY",
    "MAX_FUNC_PARAMS",
    "MAX_LOC",
    "MCCABE_THRESHOLD",
    "MIN_PROGRESS",
    "NESTING_DEPTH_LIMIT",
    "PSI_PATTERNS",
    "PSI_PENALTY_BRUTAL",
    "PSI_PENALTY_NORMAL",
    "PSI_TERMS",
    "PYTEST_TIMEOUT_SECONDS",
    "SCAN_EXTENSIONS",
    "SECURITY_PATTERNS",
    "SECURITY_PENALTY_PER_FINDING",
    "SEC_TERMS",
    "SKIP_DIRS",
    "SOVEREIGN_BONUS_FACTOR",
    "STACK_MARKERS",
    "STAGNATION_LIMIT",
    "SWARM_BASE_TEMPERATURE",
    "SWARM_DEFAULT_SQUAD_SIZE",
    "SWARM_SQUAD_SIZES",
    "SWARM_TEMPERATURE_STEP",
    "SWARM_TIMEOUT_SECONDS",
    "TOTAL_SCANNER_COUNT",
]

STACK_MARKERS = {
    "node": "package.json",
    "python": "pyproject.toml",
    "swift": "Package.swift",
}

# Patterns for the Psi dimension (toxic code markers)
# Split strings to avoid self-detection
PSI_TERMS = [
    "HAC" + "K",
    "FIX" + "ME",
    "W" + "TF",
    "stu" + "pid",
    "TO" + "DO:",
    "X" + "XX",
    "KLU" + "DGE",
    "UG" + "LY",
]
PSI_PATTERNS = re.compile(r"\b(" + "|".join(PSI_TERMS) + r")\b", re.IGNORECASE)

# Patterns for the Security dimension
# Split risky keywords to avoid self-detection
SEC_TERMS = [
    r"eval\s*\(",
    r"innerH" + "TML",
    r"\.ex" + r"ec\s*\(",
    r"pass" + r"word\s*=\s*[\"']",
    r"sec" + r"ret\s*=\s*[\"']",
]
SECURITY_PATTERNS = re.compile(
    r"\b(" + "|".join(SEC_TERMS) + r")\b",
    re.IGNORECASE,
)

MAX_LOC = 500  # Lines of code threshold for architecture dimension

# ─── Relentless Loop Constants ───────────────────────────────────────
INMEJORABLE_SCORE = 95  # The "inmejorable" threshold — perfection
STAGNATION_LIMIT = 3  # Consecutive no-progress iterations before escalating
MIN_PROGRESS = 2  # Minimum score delta to count as progress
HARD_ITERATION_CAP = 50  # Absolute safety net — never exceed this

# ─── Heal Engine Constants ───────────────────────────────────────────
PYTEST_TIMEOUT_SECONDS = 120  # Max seconds for a pytest run during healing
ESCALATION_ITER_L2 = 5  # Iteration threshold to escalate to Level 2
ESCALATION_ITER_L3 = 15  # Iteration threshold to escalate to Level 3

# ─── Swarm Constants ─────────────────────────────────────────────────
SWARM_TIMEOUT_SECONDS = 240.0  # Timeout for ThoughtOrchestra synthesis
SWARM_BASE_TEMPERATURE = 0.1  # Base temperature, scales with level
SWARM_TEMPERATURE_STEP = 0.1  # Temperature increment per escalation level
SWARM_SQUAD_SIZES: dict[int, int] = {1: 3, 2: 5}  # Level → specialist count
SWARM_DEFAULT_SQUAD_SIZE = 6  # Fallback squad size for Level 3+
DEVILS_ADVOCATE_THRESHOLD = 3  # Findings count to inject Devil's Advocate

# ─── Scan & Scoring Constants ──────────────────────────────────────────
MCCABE_THRESHOLD = 10  # Max cyclomatic complexity per function
NESTING_DEPTH_LIMIT = 6  # Max structural nesting depth
INDENT_NESTING_THRESHOLD = 24  # Char indent for polyglot nesting warning
SECURITY_PENALTY_PER_FINDING = 15  # Score penalty per security finding
PSI_PENALTY_NORMAL = 5  # Psi penalty per finding (normal mode)
PSI_PENALTY_BRUTAL = 10  # Psi penalty per finding (brutal mode)
SOVEREIGN_BONUS_FACTOR = 0.3  # Multiplier for sovereign bonus (max +30)
MAX_FINDINGS_ARCH = 10  # Cap on reported architecture findings
MAX_FINDINGS_COMPLEXITY = 15  # Cap on reported complexity findings

# ─── Heal Prompts Constants ───────────────────────────────────────────
FILES_PER_ITERATION: dict[int, int] = {1: 1, 2: 3}  # Level → files
FILES_PER_ITERATION_DEFAULT = 5  # Fallback for Level 3+
HEAL_TEMPERATURES: dict[int, float] = {
    1: 0.1, 2: 0.2, 3: 0.3,
}  # Level → LLM temperature

# ─── Antipattern Constants ─────────────────────────────────────────
MAX_FUNC_PARAMS = 5  # Max recommended parameters per function
MAX_FAN_OUT = 12  # Max allowed import fan-out per module
TOTAL_SCANNER_COUNT = 6  # Number of antipattern scanners

# ─── Daemon Constants ─────────────────────────────────────────────
DAEMON_DEFAULT_SCAN_INTERVAL = 1800  # 30 minutes between scans
DAEMON_DEFAULT_TARGET_SCORE = 100  # 100 = Sovereign standard
DAEMON_DIM_SCORE_THRESHOLD = 7  # Dimension score below this triggers query


# File extensions to scan per stack
SCAN_EXTENSIONS = {
    "node": {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"},
    "python": {".py"},
    "swift": {".swift"},
    "unknown": {".js", ".ts", ".py", ".swift"},
}

# Directories to always skip
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".svelte-kit",
    "vendor",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "tests",
    "test",
    "scripts",  # Ignore test and script directories for Psis/Security
    "pydantic-ai",
    "openclaw-re",
    "sonic-supreme",
    "omni-translate-web",
    "impact-web",
    "cortex-sovereign-web",
    "cortex_hive_ui",
    "sacrificial_project",
}
