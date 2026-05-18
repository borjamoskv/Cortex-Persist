"""CORTEX Guard Daemon — Action Classifier.

Deterministic classification of filesystem events into guard-routable
action types. O(1) pattern matching via pre-compiled rule sets.

Classification Matrix:
    .env / secrets       → P0 CRITICAL (secret_access)
    rm -rf / DROP TABLE  → P0 CRITICAL (destructive_cmd)
    requirements.txt     → P1 HIGH    (dep_change)
    alembic / migrate    → P1 HIGH    (migration)
    .py / .ts / .rs      → P2 MEDIUM  (code_mutation)
    pytest / ruff / git   → PASSTHROUGH (read_only)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ActionType(str, Enum):
    """Classified action types for guard routing."""

    SECRET_ACCESS = "secret_access"  # noqa: S105
    DESTRUCTIVE_CMD = "destructive_cmd"
    DEP_CHANGE = "dep_change"
    MIGRATION = "migration"
    CODE_MUTATION = "code_mutation"
    CONFIG_CHANGE = "config_change"
    READ_ONLY = "read_only"
    UNKNOWN = "unknown"


class GuardLevel(str, Enum):
    """Guard routing priority level."""

    P0_CRITICAL = "P0"
    P1_HIGH = "P1"
    P2_ADVISORY = "P2"
    PASSTHROUGH = "PASS"


@dataclass(frozen=True)
class ClassifiedAction:
    """Result of action classification."""

    action_type: ActionType
    guard_level: GuardLevel
    path: str
    detail: str = ""


# Pre-compiled patterns for O(1) classification
_SECRET_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.local",
    ".env.production",
    ".env.secret",
    "credentials",
    "secrets.yaml",
    "secrets.json",
    ".pem",
    ".key",
    ".p12",
    "keystore",
)

_DEP_FILES: tuple[str, ...] = (
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Gemfile",
    "Gemfile.lock",
)

_MIGRATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"alembic", re.IGNORECASE),
    re.compile(r"migrations?/", re.IGNORECASE),
    re.compile(r"migrate", re.IGNORECASE),
)

_CODE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".rs",
        ".go",
        ".java",
        ".kt",
        ".swift",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rb",
        ".ex",
        ".exs",
        ".sol",
        ".vy",
    }
)

_CONFIG_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".ini",
        ".cfg",
        ".conf",
        ".xml",
    }
)

_PASSTHROUGH_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".so",
        ".dylib",
        ".log",
        ".tmp",
        ".swp",
        ".swo",
    }
)


@dataclass
class ActionClassifier:
    """Deterministic action classifier for filesystem events.

    Pre-compiles all patterns at init for O(1) classification.
    Configurable ignore patterns from policy.
    """

    ignore_patterns: list[str] = field(
        default_factory=lambda: [
            "*.pyc",
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            ".mypy_cache",
            ".ruff_cache",
            ".pytest_cache",
        ]
    )
    passthrough_commands: list[str] = field(
        default_factory=lambda: [
            "git status",
            "git log",
            "git diff",
            "ruff check",
            "pytest",
            "ls",
            "cat",
            "head",
            "tail",
            "grep",
            "find",
            "python -m pytest",
            "mypy",
            "pyright",
        ]
    )

    _compiled_ignore: list[re.Pattern[str]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._compiled_ignore = []
        for pattern in self.ignore_patterns:
            # Convert glob to regex
            regex = pattern.replace(".", r"\.").replace("*", ".*")
            self._compiled_ignore.append(re.compile(regex))

    def should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored entirely."""
        for compiled in self._compiled_ignore:
            if compiled.search(path):
                return True
        return False

    def classify_file_event(self, path: str) -> ClassifiedAction:
        """Classify a filesystem change event.

        Args:
            path: Absolute or relative path of the changed file.

        Returns:
            ClassifiedAction with type, guard level, and context.
        """
        if self.should_ignore(path):
            return ClassifiedAction(
                action_type=ActionType.READ_ONLY,
                guard_level=GuardLevel.PASSTHROUGH,
                path=path,
                detail="ignored_pattern",
            )

        p = Path(path)
        name = p.name.lower()
        suffix = p.suffix.lower()

        # P0: Secret files
        for secret_pattern in _SECRET_PATTERNS:
            if name == secret_pattern or name.endswith(secret_pattern):
                return ClassifiedAction(
                    action_type=ActionType.SECRET_ACCESS,
                    guard_level=GuardLevel.P0_CRITICAL,
                    path=path,
                    detail=f"Secret file modified: {name}",
                )

        # P1: Dependency files
        if name in {d.lower() for d in _DEP_FILES}:
            # Lock files are lower priority
            if name.endswith(".lock") or name.endswith("-lock.json"):
                return ClassifiedAction(
                    action_type=ActionType.DEP_CHANGE,
                    guard_level=GuardLevel.P2_ADVISORY,
                    path=path,
                    detail=f"Lock file updated: {name}",
                )
            return ClassifiedAction(
                action_type=ActionType.DEP_CHANGE,
                guard_level=GuardLevel.P1_HIGH,
                path=path,
                detail=f"Dependency manifest changed: {name}",
            )

        # P1: Migration files
        path_str = str(p)
        for migration_re in _MIGRATION_PATTERNS:
            if migration_re.search(path_str):
                return ClassifiedAction(
                    action_type=ActionType.MIGRATION,
                    guard_level=GuardLevel.P1_HIGH,
                    path=path,
                    detail=f"Migration file detected: {name}",
                )

        # P2: Code mutations
        if suffix in _CODE_EXTENSIONS:
            return ClassifiedAction(
                action_type=ActionType.CODE_MUTATION,
                guard_level=GuardLevel.P2_ADVISORY,
                path=path,
                detail=f"Code file modified: {name}",
            )

        # P2: Config changes
        if suffix in _CONFIG_EXTENSIONS:
            return ClassifiedAction(
                action_type=ActionType.CONFIG_CHANGE,
                guard_level=GuardLevel.P2_ADVISORY,
                path=path,
                detail=f"Config file modified: {name}",
            )

        # Passthrough: compiled / temp files
        if suffix in _PASSTHROUGH_EXTENSIONS:
            return ClassifiedAction(
                action_type=ActionType.READ_ONLY,
                guard_level=GuardLevel.PASSTHROUGH,
                path=path,
                detail="compiled_or_temp",
            )

        return ClassifiedAction(
            action_type=ActionType.UNKNOWN,
            guard_level=GuardLevel.P2_ADVISORY,
            path=path,
            detail=f"Unclassified file: {name}",
        )

    def classify_command(self, command: str) -> ClassifiedAction:
        """Classify a terminal command.

        Args:
            command: The command string being executed.

        Returns:
            ClassifiedAction with type and guard level.
        """
        cmd_lower = command.strip().lower()

        # Passthrough: known safe commands
        for safe_cmd in self.passthrough_commands:
            if cmd_lower.startswith(safe_cmd):
                return ClassifiedAction(
                    action_type=ActionType.READ_ONLY,
                    guard_level=GuardLevel.PASSTHROUGH,
                    path="",
                    detail=f"Safe command: {command[:80]}",
                )

        # P0: Destructive commands
        destructive = [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf .",
            "drop table",
            "drop database",
            "truncate table",
            "format c:",
            "mkfs",
            "dd if=/dev/zero",
            "> /dev/sda",
            "chmod -R 777 /",
        ]
        for pattern in destructive:
            if pattern in cmd_lower:
                return ClassifiedAction(
                    action_type=ActionType.DESTRUCTIVE_CMD,
                    guard_level=GuardLevel.P0_CRITICAL,
                    path="",
                    detail=f"Destructive command: {command[:80]}",
                )

        # P1: Package install commands
        install_patterns = [
            "pip install",
            "npm install",
            "yarn add",
            "cargo add",
            "go get",
            "gem install",
            "apt install",
            "brew install",
        ]
        for pattern in install_patterns:
            if pattern in cmd_lower:
                return ClassifiedAction(
                    action_type=ActionType.DEP_CHANGE,
                    guard_level=GuardLevel.P1_HIGH,
                    path="",
                    detail=f"Package install: {command[:80]}",
                )

        # Default: code mutation (unknown command modifying state)
        return ClassifiedAction(
            action_type=ActionType.CODE_MUTATION,
            guard_level=GuardLevel.P2_ADVISORY,
            path="",
            detail=f"Command: {command[:80]}",
        )
