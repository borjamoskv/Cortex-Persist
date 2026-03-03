# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""AlphaCode — Competitive Programming Sandbox Runner.

Extends CORTEX's ASTSandbox for competitive programming:
- stdin/stdout capture for test case I/O
- Subprocess isolation for untrusted C++/JS
- Deterministic timeout enforcement
- Output normalization for clustering
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Final

from cortex.alphacode._models import (
    FilteredSolution,
    Language,
    SampledSolution,
    SolutionStatus,
    TestCase,
    TestResult,
)

logger = logging.getLogger("cortex.alphacode.runner")

_PYTHON_CMD: Final[str] = "python3"
_CPP_COMPILER: Final[str] = "g++"
_NODE_CMD: Final[str] = "node"


def _normalize_output(raw: str) -> str:
    """Normalize output: strip trailing whitespace per line, trailing newline."""
    lines = raw.rstrip("\n").split("\n")
    return "\n".join(line.rstrip() for line in lines)


class SandboxRunner:
    """Execute candidate solutions against test cases in isolated subprocesses.

    Unlike the AST sandbox, this uses subprocess isolation to support:
    - stdin/stdout I/O (competitive programming format)
    - Compiled languages (C++)
    - Hard timeout enforcement via process kill
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        memory_limit_mb: int = 256,
        temp_dir: Path | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._memory_limit_mb = memory_limit_mb
        self._temp_dir = temp_dir or Path(tempfile.gettempdir()) / "cortex_alphacode"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    async def run_solution(
        self,
        solution: SampledSolution,
        test_cases: list[TestCase],
        language: Language = Language.PYTHON,
    ) -> FilteredSolution:
        """Run a solution against all test cases. Returns FilteredSolution."""
        results: list[TestResult] = []

        for i, test in enumerate(test_cases):
            result = await self._execute_single(
                code=solution.code,
                test_input=test.input,
                expected_output=test.expected_output,
                test_index=i,
                language=language,
            )
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        pass_rate = passed / total if total > 0 else 0.0

        if pass_rate == 1.0:
            status = SolutionStatus.PASSED
        elif any(r.error and "timeout" in r.error.lower() for r in results):
            status = SolutionStatus.TIMEOUT
        elif any(r.error and "compile" in r.error.lower() for r in results):
            status = SolutionStatus.COMPILE_ERROR
        elif any(r.error for r in results):
            status = SolutionStatus.RUNTIME_ERROR
        else:
            status = SolutionStatus.FAILED

        return FilteredSolution(
            code=solution.code,
            code_hash=solution.code_hash,
            sample_index=solution.sample_index,
            status=status,
            test_results=tuple(results),
            pass_rate=pass_rate,
        )

    async def _execute_single(
        self,
        code: str,
        test_input: str,
        expected_output: str,
        test_index: int,
        language: Language,
    ) -> TestResult:
        """Execute code with stdin and capture stdout."""
        start = time.monotonic()

        try:
            if language == Language.PYTHON:
                actual = await self._run_python(code, test_input)
            elif language == Language.CPP:
                actual = await self._run_cpp(code, test_input)
            elif language == Language.JAVASCRIPT:
                actual = await self._run_javascript(code, test_input)
            else:
                return TestResult(
                    test_index=test_index,
                    passed=False,
                    actual_output="",
                    expected_output=expected_output,
                    execution_time_ms=(time.monotonic() - start) * 1000,
                    error=f"Unsupported language: {language}",
                )
        except TimeoutError:
            return TestResult(
                test_index=test_index,
                passed=False,
                actual_output="",
                expected_output=expected_output,
                execution_time_ms=(time.monotonic() - start) * 1000,
                error=f"Timeout after {self._timeout}s",
            )
        except subprocess.CalledProcessError as e:
            return TestResult(
                test_index=test_index,
                passed=False,
                actual_output=e.stdout or "",
                expected_output=expected_output,
                execution_time_ms=(time.monotonic() - start) * 1000,
                error=f"Runtime error: {e.stderr or str(e)}",
            )
        except OSError as e:
            return TestResult(
                test_index=test_index,
                passed=False,
                actual_output="",
                expected_output=expected_output,
                execution_time_ms=(time.monotonic() - start) * 1000,
                error=f"OS error: {e}",
            )

        elapsed = (time.monotonic() - start) * 1000
        norm_actual = _normalize_output(actual)
        norm_expected = _normalize_output(expected_output)
        passed = norm_actual == norm_expected

        return TestResult(
            test_index=test_index,
            passed=passed,
            actual_output=norm_actual,
            expected_output=norm_expected,
            execution_time_ms=elapsed,
        )

    async def _run_python(self, code: str, stdin_data: str) -> str:
        """Run Python code in subprocess with stdin."""
        proc = await asyncio.create_subprocess_exec(
            _PYTHON_CMD,
            "-c",
            code,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TimeoutError(f"Python execution exceeded {self._timeout}s") from None

        if proc.returncode != 0:
            err = subprocess.CalledProcessError(
                proc.returncode, _PYTHON_CMD,
            )
            err.stdout = stdout.decode(errors="replace")
            err.stderr = stderr.decode(errors="replace")
            raise err
        return stdout.decode(errors="replace")

    async def _run_cpp(self, code: str, stdin_data: str) -> str:
        """Compile and run C++ code."""
        src_file = self._temp_dir / f"sol_{hash(code) & 0xFFFFFFFF}.cpp"
        bin_file = src_file.with_suffix("")

        src_file.write_text(code, encoding="utf-8")

        # Compile
        compile_proc = await asyncio.create_subprocess_exec(
            _CPP_COMPILER,
            "-O2",
            "-std=c++17",
            "-o",
            str(bin_file),
            str(src_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(
                compile_proc.communicate(), timeout=30.0
            )
        except asyncio.TimeoutError:
            compile_proc.kill()
            await compile_proc.wait()
            raise TimeoutError("C++ compilation exceeded 30s") from None

        if compile_proc.returncode != 0:
            err = subprocess.CalledProcessError(
                compile_proc.returncode, _CPP_COMPILER,
            )
            err.stderr = f"Compile error: {stderr.decode(errors='replace')}"
            raise err

        # Run
        try:
            proc = await asyncio.create_subprocess_exec(
                str(bin_file),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_data.encode()),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise TimeoutError(
                    f"C++ execution exceeded {self._timeout}s"
                ) from None

            if proc.returncode != 0:
                err = subprocess.CalledProcessError(
                    proc.returncode, str(bin_file),
                )
                err.stdout = stdout.decode(errors="replace")
                err.stderr = stderr.decode(errors="replace")
                raise err
            return stdout.decode(errors="replace")
        finally:
            # Cleanup compiled binary
            bin_file.unlink(missing_ok=True)
            src_file.unlink(missing_ok=True)

    async def _run_javascript(self, code: str, stdin_data: str) -> str:
        """Run JavaScript code via Node.js."""
        proc = await asyncio.create_subprocess_exec(
            _NODE_CMD,
            "-e",
            code,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TimeoutError(
                f"JavaScript execution exceeded {self._timeout}s"
            ) from None

        if proc.returncode != 0:
            err = subprocess.CalledProcessError(
                proc.returncode, _NODE_CMD,
            )
            err.stdout = stdout.decode(errors="replace")
            err.stderr = stderr.decode(errors="replace")
            raise err
        return stdout.decode(errors="replace")

    async def get_output_for_input(
        self,
        code: str,
        test_input: str,
        language: Language = Language.PYTHON,
    ) -> str:
        """Execute code and return raw output (for clustering signatures)."""
        try:
            if language == Language.PYTHON:
                return await self._run_python(code, test_input)
            elif language == Language.CPP:
                return await self._run_cpp(code, test_input)
            elif language == Language.JAVASCRIPT:
                return await self._run_javascript(code, test_input)
        except (TimeoutError, subprocess.CalledProcessError, OSError):
            return "<ERROR>"
        return "<UNSUPPORTED>"
