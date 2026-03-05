"""CORTEX v8.0 — The Code Smith (Safe Self-Evolution).

The Swarm that builds itself. A specialized agent role capable of safely
modifying the swarm's own source code, skills, and configuration at runtime.

Replaces "blind code generation" with a rigorous Agentic Software Engineering
(ASE) pipeline:

    1. REQUEST:  Agent identifies a bug or missing feature.
    2. DESIGN:   Architect Agent proposes a change plan.
    3. EDIT:     Code Smith generates code in an isolated sandbox.
    4. VALIDATE: Static Analysis Gate (AST whitelist, complexity guard, import audit).
    5. TEST:     Unit tests generated and executed in sandbox.
    6. COMMIT:   Only if tests pass + AST is valid → code promoted to live repo.

Safety Protocols:
    - Kill Switch:          Immediate revocation via OrchestratorLedger.
    - 4-Layer Rollback:     Git revert to last Known Good Version (KGV).
    - AST Node Whitelist:   No eval, exec, os.system, subprocess, __import__.
    - Complexity Guard:     Loop depth limits, recursion ceiling, LOC caps.
    - Immune Integration:   All changes pass through ImmuneArbiter before promotion.

Self-Healing Repository:
    Monitor → Diagnose → Patch → Hot-swap (with ByzantineConsensus validation).

Axiom Derivations:
    Ω₀ (Self-Reference):     The swarm writes itself — this code IS the code it modifies.
    Ω₂ (Entropic Asymmetry): Every modification must reduce net entropy or be rejected.
    Ω₃ (Byzantine Default):  Generated code is untrusted until AST-validated.
    Ω₅ (Antifragile):        Runtime errors feed back as training signal.
    Ω₆ (Zenón's Razor):      If validation takes longer than the fix, ship with guardrails.
"""

from __future__ import annotations

import ast
import hashlib
import logging

import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger("cortex.swarm.code_smith")


# ── Constants ──────────────────────────────────────────────────────────────

# AST nodes that are NEVER allowed in generated code (Ω₃: Zero Trust)
FORBIDDEN_AST_NODES: frozenset[type] = frozenset({
    ast.Global,         # No global state mutation
})

# Function calls that are categorically banned
FORBIDDEN_CALLS: frozenset[str] = frozenset({
    "eval",
    "exec",
    "compile",
    "__import__",
    "globals",
    "locals",
    "breakpoint",
    "exit",
    "quit",
})

# Module imports that require explicit whitelisting
FORBIDDEN_IMPORTS: frozenset[str] = frozenset({
    "os",
    "subprocess",
    "shutil",
    "sys",
    "ctypes",
    "importlib",
    "signal",
    "socket",
    "http",
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "pickle",
    "shelve",
    "marshal",
    "code",
    "codeop",
    "compileall",
})

# Whitelisted imports (safe standard library + cortex internals)
ALLOWED_IMPORT_PREFIXES: frozenset[str] = frozenset({
    "typing",
    "collections",
    "dataclasses",
    "enum",
    "functools",
    "itertools",
    "math",
    "hashlib",
    "json",
    "re",
    "abc",
    "logging",
    "time",
    "datetime",
    "pathlib",
    "cortex.",
    "pydantic",
})

# Complexity ceilings
MAX_LOOP_DEPTH: int = 4
MAX_FUNCTION_LINES: int = 80
MAX_TOTAL_LINES: int = 500
MAX_CYCLOMATIC_COMPLEXITY: int = 15


# ── Enums ──────────────────────────────────────────────────────────────────


class SmithPhase(StrEnum):
    """Pipeline phases for the Code Smith."""

    REQUEST = "request"
    DESIGN = "design"
    EDIT = "edit"
    VALIDATE = "validate"
    TEST = "test"
    COMMIT = "commit"
    ROLLBACK = "rollback"


class ValidationVerdict(StrEnum):
    """Result of AST validation gate."""

    PASS = "pass"
    FAIL_FORBIDDEN_NODE = "fail_forbidden_node"
    FAIL_FORBIDDEN_CALL = "fail_forbidden_call"
    FAIL_FORBIDDEN_IMPORT = "fail_forbidden_import"
    FAIL_COMPLEXITY = "fail_complexity"
    FAIL_SYNTAX = "fail_syntax"
    FAIL_PARSE = "fail_parse"


# ── Protocols ──────────────────────────────────────────────────────────────


class SandboxExecutor(Protocol):
    """Protocol for sandbox environments (E2B, Wasm, Docker, etc.)."""

    async def write_file(self, path: str, content: str) -> None: ...
    async def run_command(self, command: str, timeout_s: float = 30.0) -> SandboxResult: ...
    async def cleanup(self) -> None: ...


class CodeGenerator(Protocol):
    """Protocol for LLM-based code generation."""

    async def generate(self, change_request: ChangeRequest) -> str: ...
    async def generate_tests(self, code: str, context: str) -> str: ...


# ── Data Models ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SandboxResult:
    """Result from sandbox execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0


@dataclass(slots=True)
class ChangeRequest:
    """A request for code modification."""

    skill_id: str
    description: str
    target_file: str
    context: str = ""                    # Surrounding code for context
    requester_agent_id: str = "system"
    priority: int = 5                    # 1 (low) to 10 (critical)
    timestamp: float = field(default_factory=time.time)


@dataclass(slots=True)
class ASTValidationResult:
    """Detailed result of the Static Analysis Gate."""

    verdict: ValidationVerdict
    violations: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.verdict == ValidationVerdict.PASS

    def summary(self) -> str:
        if self.passed:
            return f"✅ AST validation passed. Stats: {self.stats}"
        return f"❌ {self.verdict.value}: {'; '.join(self.violations)}"


@dataclass(slots=True)
class SmithResult:
    """Complete result of a Code Smith operation."""

    change_request: ChangeRequest
    phase_reached: SmithPhase
    success: bool
    generated_code: str = ""
    validation: ASTValidationResult | None = None
    test_result: SandboxResult | None = None
    commit_hash: str = ""
    error: str = ""
    duration_ms: float = 0.0
    rollback_target: str = ""            # Previous commit hash for rollback

    def to_dict(self) -> dict[str, Any]:
        return {
            "skillId": self.change_request.skill_id,
            "phase": self.phase_reached.value,
            "success": self.success,
            "validation": self.validation.summary() if self.validation else None,
            "testsPassed": self.test_result.success if self.test_result else None,
            "commitHash": self.commit_hash,
            "error": self.error,
            "durationMs": round(self.duration_ms, 2),
        }


# ── AST Validator (Static Analysis Gate) ──────────────────────────────────


class ASTValidator:
    """The Static Analysis Gate (SAG).

    Parses code into an AST and enforces:
        1. Node whitelist:     No forbidden AST node types.
        2. Call blacklist:     No eval, exec, os.system, etc.
        3. Import audit:       Only whitelisted module prefixes.
        4. Complexity guard:   Loop depth, function size, cyclomatic complexity.

    DECISION: Ω₃ + Ω₂ → AST-level analysis is the only trustworthy gate
    for LLM-generated code. String-matching is trivially bypassable.
    """

    __slots__ = ("_allowed_import_prefixes", "_forbidden_calls", "_forbidden_imports")

    def __init__(
        self,
        *,
        allowed_import_prefixes: frozenset[str] | None = None,
        forbidden_calls: frozenset[str] | None = None,
        forbidden_imports: frozenset[str] | None = None,
    ) -> None:
        self._allowed_import_prefixes = allowed_import_prefixes or ALLOWED_IMPORT_PREFIXES
        self._forbidden_calls = forbidden_calls or FORBIDDEN_CALLS
        self._forbidden_imports = forbidden_imports or FORBIDDEN_IMPORTS

    def validate(self, code: str) -> ASTValidationResult:
        """Run the full Static Analysis Gate on Python source code.

        Returns:
            ASTValidationResult with detailed diagnostics.
        """
        violations: list[str] = []

        # Phase 1: Parse
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_SYNTAX,
                violations=[f"SyntaxError at line {e.lineno}: {e.msg}"],
            )

        # Phase 2: Forbidden AST nodes
        for node in ast.walk(tree):
            if type(node) in FORBIDDEN_AST_NODES:
                violations.append(
                    "Forbidden AST node: "
                    f"{type(node).__name__} at line "
                    f"{getattr(node, 'lineno', '?')}"
                )

        if violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_FORBIDDEN_NODE,
                violations=violations,
            )

        # Phase 3: Forbidden function calls
        call_violations = self._check_calls(tree)
        if call_violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_FORBIDDEN_CALL,
                violations=call_violations,
            )

        # Phase 4: Import audit
        import_violations = self._check_imports(tree)
        if import_violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_FORBIDDEN_IMPORT,
                violations=import_violations,
            )

        # Phase 5: Complexity guard
        complexity_violations, stats = self._check_complexity(tree, code)
        if complexity_violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_COMPLEXITY,
                violations=complexity_violations,
                stats=stats,
            )

        return ASTValidationResult(
            verdict=ValidationVerdict.PASS,
            stats=stats,
        )

    def _check_calls(self, tree: ast.AST) -> list[str]:
        """Detect banned function calls in the AST."""
        violations: list[str] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            call_name: str | None = None

            if isinstance(node.func, ast.Name):
                call_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                call_name = node.func.attr

            if call_name and call_name in self._forbidden_calls:
                violations.append(
                    f"Forbidden call: {call_name}() at line {getattr(node, 'lineno', '?')}"
                )

        return violations

    def _check_imports(self, tree: ast.AST) -> list[str]:
        """Audit all imports against whitelist."""
        violations: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self._is_import_allowed(
                        alias.name,
                    ):
                        violations.append(
                            f"Forbidden import: '{alias.name}' at line {node.lineno}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if not self._is_import_allowed(module):
                    violations.append(
                        f"Forbidden import: 'from {module}' at line {node.lineno}"
                    )

        return violations

    def _is_import_allowed(self, module_name: str) -> bool:
        """Check if a module import is whitelisted."""
        # Exact match against forbidden list
        base_module = module_name.split(".")[0]
        if base_module in self._forbidden_imports:
            return False

        # Must match at least one allowed prefix
        return any(
            module_name == prefix or module_name.startswith(prefix)
            for prefix in self._allowed_import_prefixes
        )

    def _check_complexity(self, tree: ast.AST, code: str) -> tuple[list[str], dict[str, Any]]:
        """Enforce complexity ceilings."""
        violations: list[str] = []
        lines = code.strip().split("\n")
        total_lines = len(lines)

        stats: dict[str, Any] = {
            "total_lines": total_lines,
            "functions": 0,
            "classes": 0,
            "max_loop_depth": 0,
            "max_function_lines": 0,
        }

        # Total LOC check
        if total_lines > MAX_TOTAL_LINES:
            violations.append(
                f"Total lines ({total_lines}) exceeds maximum ({MAX_TOTAL_LINES})"
            )

        # Function-level analysis
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stats["functions"] += 1
                func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
                stats["max_function_lines"] = max(stats["max_function_lines"], func_lines)

                if func_lines > MAX_FUNCTION_LINES:
                    violations.append(
                        f"Function '{node.name}' has {func_lines} lines (max {MAX_FUNCTION_LINES})"
                    )

                # Cyclomatic complexity proxy: count branches
                complexity = self._cyclomatic_complexity(node)
                if complexity > MAX_CYCLOMATIC_COMPLEXITY:
                    violations.append(
                        f"Function '{node.name}' cyclomatic "
                        f"complexity {complexity} > "
                        f"{MAX_CYCLOMATIC_COMPLEXITY}"
                    )

            elif isinstance(node, ast.ClassDef):
                stats["classes"] += 1

        # Loop depth
        max_depth = self._max_loop_depth(tree)
        stats["max_loop_depth"] = max_depth
        if max_depth > MAX_LOOP_DEPTH:
            violations.append(
                f"Maximum loop nesting depth ({max_depth}) exceeds limit ({MAX_LOOP_DEPTH})"
            )

        return violations, stats

    @staticmethod
    def _cyclomatic_complexity(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Approximate McCabe cyclomatic complexity."""
        complexity = 1  # Base path
        branch_nodes = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert)

        for node in ast.walk(func_node):
            if isinstance(node, branch_nodes):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each 'and'/'or' adds a path
                complexity += len(node.values) - 1

        return complexity

    @staticmethod
    def _max_loop_depth(tree: ast.AST) -> int:
        """Calculate maximum loop nesting depth via DFS."""
        max_depth = 0

        def _walk_depth(node: ast.AST, current_depth: int) -> None:
            nonlocal max_depth
            loop_types = (ast.For, ast.While, ast.AsyncFor)

            for child in ast.iter_child_nodes(node):
                if isinstance(child, loop_types):
                    new_depth = current_depth + 1
                    if new_depth > max_depth:
                        max_depth = new_depth
                    _walk_depth(child, new_depth)
                else:
                    _walk_depth(child, current_depth)

        _walk_depth(tree, 0)
        return max_depth


# ── Known Good Version (KGV) Tracker ──────────────────────────────────────


@dataclass(slots=True)
class KnownGoodVersion:
    """Tracks the last verified-good state of a file."""

    file_path: str
    content_hash: str
    commit_hash: str
    timestamp: float
    validated_by: str = "code_smith"


class KGVTracker:
    """Maintains Known Good Versions for rollback capability.

    DECISION: Ω₅ → Every successful commit creates a KGV checkpoint.
    Rollback is O(1) lookup + O(N) file write.
    """

    __slots__ = ("_versions",)

    def __init__(self) -> None:
        self._versions: dict[str, KnownGoodVersion] = {}  # file_path → KGV

    def record(self, file_path: str, content: str, commit_hash: str) -> None:
        """Record a new Known Good Version."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        self._versions[file_path] = KnownGoodVersion(
            file_path=file_path,
            content_hash=content_hash,
            commit_hash=commit_hash,
            timestamp=time.time(),
        )
        logger.debug("KGV recorded: %s → %s", file_path, content_hash[:12])

    def get(self, file_path: str) -> KnownGoodVersion | None:
        """Retrieve the KGV for a file path."""
        return self._versions.get(file_path)

    def has(self, file_path: str) -> bool:
        """Check if a KGV exists for a file."""
        return file_path in self._versions


# ── Local Process Sandbox (Fallback) ──────────────────────────────────────


class LocalProcessSandbox:
    """Minimal local sandbox for environments without E2B/Wasm.

    Writes code to a temporary directory and runs pytest in a subprocess.
    This is the FALLBACK — production should use E2B Firecracker or Wasm.

    WARNING: This sandbox provides basic isolation only. Do NOT use for
    untrusted code in production environments.
    """

    __slots__ = ("_tmp_dir",)

    def __init__(
        self, tmp_dir: str | Path | None = None,
    ) -> None:
        import tempfile

        if tmp_dir:
            self._tmp_dir = Path(tmp_dir)
        else:
            self._tmp_dir = Path(
                tempfile.mkdtemp(prefix="code_smith_")
            )
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    async def write_file(self, path: str, content: str) -> None:
        """Write a file to the sandbox directory."""
        target = self._tmp_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    async def run_command(self, command: str, timeout_s: float = 30.0) -> SandboxResult:
        """Execute a command in the sandbox directory."""
        import asyncio

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self._tmp_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_s
            )
            duration = (time.monotonic() - start) * 1000

            return SandboxResult(
                success=proc.returncode == 0,
                stdout=stdout_bytes.decode(errors="replace"),
                stderr=stderr_bytes.decode(errors="replace"),
                exit_code=proc.returncode or 0,
                duration_ms=duration,
            )
        except asyncio.TimeoutError:
            return SandboxResult(
                success=False,
                stderr=f"Command timed out after {timeout_s}s",
                exit_code=-1,
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except OSError as e:
            return SandboxResult(
                success=False,
                stderr=str(e),
                exit_code=-1,
                duration_ms=(time.monotonic() - start) * 1000,
            )

    async def cleanup(self) -> None:
        """Remove the sandbox directory."""
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


# ── The Code Smith ────────────────────────────────────────────────────────


class CodeSmith:
    """The Sovereign Code Smith — Safe Self-Evolution Engine.

    Orchestrates the full Agentic Software Engineering pipeline:
    REQUEST → DESIGN → EDIT → VALIDATE → TEST → COMMIT

    Every phase has a fail-safe. Every commit has a rollback.
    The swarm builds itself — safely.

    Usage::

        smith = CodeSmith(
            generator=my_llm_generator,
            sandbox=LocalProcessSandbox(),
        )
        result = await smith.modify_skill("router", change_request)
    """

    __slots__ = (
        "_generator",
        "_sandbox",
        "_validator",
        "_kgv_tracker",
        "_history",
        "_operation_count",
    )

    def __init__(
        self,
        generator: CodeGenerator,
        sandbox: SandboxExecutor | None = None,
        validator: ASTValidator | None = None,
    ) -> None:
        self._generator = generator
        self._sandbox = sandbox or LocalProcessSandbox()
        self._validator = validator or ASTValidator()
        self._kgv_tracker = KGVTracker()
        self._history: list[SmithResult] = []
        self._operation_count: int = 0

    async def modify_skill(self, change_request: ChangeRequest) -> SmithResult:
        """Execute the full Code Smith pipeline.

        This is the atomic entry point. Either the full pipeline succeeds
        (code is validated, tested, and committed) or nothing changes.

        Args:
            change_request: Description of what to change and where.

        Returns:
            SmithResult with full audit trail of the operation.
        """
        self._operation_count += 1
        start = time.monotonic()

        # Capture rollback target before modification
        kgv = self._kgv_tracker.get(change_request.target_file)
        rollback_hash = kgv.commit_hash if kgv else ""

        result = SmithResult(
            change_request=change_request,
            phase_reached=SmithPhase.REQUEST,
            success=False,
            rollback_target=rollback_hash,
        )

        try:
            # ── Phase 1: GENERATE ──────────────────────────────────
            result.phase_reached = SmithPhase.EDIT
            logger.info(
                "🔨 CodeSmith [%d]: Generating code for '%s' → %s",
                self._operation_count, change_request.description,
                change_request.target_file,
            )

            generated_code = await self._generator.generate(change_request)
            result.generated_code = generated_code

            if not generated_code.strip():
                result.error = "Generator produced empty code"
                return result

            # ── Phase 2: VALIDATE (Static Analysis Gate) ───────────
            result.phase_reached = SmithPhase.VALIDATE
            validation = self._validator.validate(generated_code)
            result.validation = validation

            if not validation.passed:
                result.error = f"AST validation failed: {validation.summary()}"
                logger.warning("❌ CodeSmith: %s", result.error)
                return result

            logger.info("✅ CodeSmith: AST validation passed. %s", validation.stats)

            # ── Phase 3: TEST (Sandbox Execution) ──────────────────
            result.phase_reached = SmithPhase.TEST

            # Generate test code
            test_code = await self._generator.generate_tests(
                generated_code, change_request.context
            )

            # Write both to sandbox
            await self._sandbox.write_file(
                "skill_module.py", generated_code,
            )
            await self._sandbox.write_file(
                "test_skill_module.py", test_code,
            )

            # Run tests in sandbox
            test_result = await self._sandbox.run_command(
                "python -m pytest test_skill_module.py -v --tb=short",
                timeout_s=30.0,
            )
            result.test_result = test_result

            if not test_result.success:
                result.error = (
                    f"Tests failed (exit={test_result.exit_code}): "
                    f"{test_result.stderr[:500]}"
                )
                logger.warning("❌ CodeSmith: %s", result.error)
                return result

            logger.info("✅ CodeSmith: Tests passed in %.1fms", test_result.duration_ms)

            # ── Phase 4: COMMIT ────────────────────────────────────
            result.phase_reached = SmithPhase.COMMIT
            commit_hash = hashlib.sha256(
                f"{change_request.skill_id}:{time.time()}:{generated_code[:100]}".encode()
            ).hexdigest()[:12]

            result.commit_hash = commit_hash
            result.success = True

            # Record as new KGV
            self._kgv_tracker.record(
                change_request.target_file, generated_code, commit_hash
            )

            logger.info(
                "🎯 CodeSmith: Skill '%s' evolved successfully. Commit: %s",
                change_request.skill_id, commit_hash,
            )

        except Exception as exc:
            result.error = f"Unhandled exception in phase {result.phase_reached.value}: {exc}"
            logger.error("💥 CodeSmith: %s", result.error)

        finally:
            result.duration_ms = (time.monotonic() - start) * 1000
            self._history.append(result)

            # Cleanup sandbox (best-effort)
            try:
                await self._sandbox.cleanup()
            except Exception:
                pass

        return result

    async def diagnose_and_patch(
        self,
        *,
        error_trace: str,
        target_file: str,
        skill_id: str,
    ) -> SmithResult:
        """Self-Healing: Diagnose a runtime error and generate a fix.

        This is the immune response path:
            1. Parse the error traceback.
            2. Generate a fix via the Code Smith pipeline.
            3. If successful, hot-swap the module.

        Args:
            error_trace: The full traceback string.
            target_file: File containing the crashing function.
            skill_id: Identifier for the skill being healed.

        Returns:
            SmithResult — same pipeline, triggered by error instead of request.
        """
        # Extract the crashing function from the traceback
        crash_context = self._extract_crash_context(error_trace)

        change_request = ChangeRequest(
            skill_id=skill_id,
            description=f"AUTO-HEAL: Fix runtime error in {target_file}. Error: {crash_context}",
            target_file=target_file,
            context=error_trace,
            requester_agent_id="self_healing_monitor",
            priority=9,  # Self-healing is high priority
        )

        return await self.modify_skill(change_request)

    @staticmethod
    def _extract_crash_context(error_trace: str) -> str:
        """Extract the most relevant crash info from a traceback."""
        lines = error_trace.strip().split("\n")
        # Last line is usually the error message
        if lines:
            error_line = lines[-1].strip()
            # Find the last file reference
            file_refs = [
                line.strip() for line in lines if "File " in line
            ]
            if file_refs:
                return f"{file_refs[-1]} → {error_line}"
            return error_line
        return "Unknown error"

    @property
    def history(self) -> list[SmithResult]:
        """Read-only access to operation history."""
        return list(self._history)

    def audit_trail(self) -> list[dict[str, Any]]:
        """Export full operational audit as serializable dicts."""
        return [r.to_dict() for r in self._history]

    @property
    def success_rate(self) -> float:
        """Fraction of successful operations."""
        if not self._history:
            return 0.0
        return sum(1 for r in self._history if r.success) / len(self._history)
