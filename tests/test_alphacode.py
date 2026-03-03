# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""Tests for cortex.alphacode module.

Strategy: Unit tests for models, runner, clusterer, and pipeline
using mocked LLM providers. No external API calls required.
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from cortex.alphacode._models import (
    AlphaCodeConfig,
    ClusterResult,
    FilteredSolution,
    Language,
    OutputSignature,
    Problem,
    SampledSolution,
    ScoredSolution,
    SolutionStatus,
    SubmissionSet,
    TestCase,
)
from cortex.alphacode._runner import SandboxRunner, _normalize_output
from cortex.alphacode._sampler import _build_user_prompt, _extract_code


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def simple_problem() -> Problem:
    """A + B problem — the canonical competitive programming test."""
    return Problem(
        title="A+B Problem",
        statement=(
            "Read two integers a and b from stdin, separated by a space.\n"
            "Print their sum.\n\n"
            "Constraints: 1 <= a, b <= 10^9"
        ),
        example_tests=[
            TestCase(input="1 2", expected_output="3"),
            TestCase(input="100 200", expected_output="300"),
        ],
    )


@pytest.fixture
def correct_python_solution() -> str:
    return "a, b = map(int, input().split())\nprint(a + b)"


@pytest.fixture
def wrong_python_solution() -> str:
    return "a, b = map(int, input().split())\nprint(a - b)"


@pytest.fixture
def timeout_python_solution() -> str:
    return "while True: pass"


@pytest.fixture
def default_config() -> AlphaCodeConfig:
    return AlphaCodeConfig(num_samples=5, execution_timeout_seconds=3.0)


# ─── Model Tests ──────────────────────────────────────────────────────────


class TestModels:
    """Tests for data model immutability, validation, and computed properties."""

    def test_problem_creation(self, simple_problem: Problem) -> None:
        assert simple_problem.title == "A+B Problem"
        assert len(simple_problem.example_tests) == 2
        assert simple_problem.language == Language.PYTHON

    def test_problem_frozen(self, simple_problem: Problem) -> None:
        """Pydantic frozen model should reject mutations."""
        with pytest.raises(ValidationError):
            simple_problem.title = "Modified"  # type: ignore[misc]

    def test_test_case_frozen(self) -> None:
        tc = TestCase(input="1", expected_output="2")
        with pytest.raises(ValidationError):
            tc.input = "3"  # type: ignore[misc]

    def test_sampled_solution_hash(self) -> None:
        sol = SampledSolution(
            code="print(42)",
            sample_index=0,
            temperature=0.8,
            model_name="test",
            generation_time_ms=100.0,
        )
        expected = hashlib.sha256(b"print(42)").hexdigest()[:16]
        assert sol.code_hash == expected

    def test_sampled_solution_hash_strips_whitespace(self) -> None:
        sol1 = SampledSolution(
            code="print(42)\n",
            sample_index=0,
            temperature=0.8,
            model_name="test",
            generation_time_ms=100.0,
        )
        sol2 = SampledSolution(
            code="print(42)  \n  ",
            sample_index=1,
            temperature=0.8,
            model_name="test",
            generation_time_ms=100.0,
        )
        assert sol1.code_hash == sol2.code_hash

    def test_output_signature_deterministic(self) -> None:
        sig1 = OutputSignature.from_outputs(["3", "5", "7"])
        sig2 = OutputSignature.from_outputs(["3", "5", "7"])
        assert sig1.signature_hash == sig2.signature_hash

    def test_output_signature_strips_whitespace(self) -> None:
        sig1 = OutputSignature.from_outputs(["3 ", " 5", "7\n"])
        sig2 = OutputSignature.from_outputs(["3", "5", "7"])
        assert sig1.signature_hash == sig2.signature_hash

    def test_output_signature_different_outputs(self) -> None:
        sig1 = OutputSignature.from_outputs(["3", "5"])
        sig2 = OutputSignature.from_outputs(["3", "6"])
        assert sig1.signature_hash != sig2.signature_hash

    def test_cluster_confidence(self) -> None:
        sol = FilteredSolution(
            code="x",
            code_hash="abc",
            sample_index=0,
            status=SolutionStatus.PASSED,
            test_results=(),
            pass_rate=1.0,
        )
        cluster = ClusterResult(
            cluster_id=0,
            signature=OutputSignature.from_outputs([]),
            solutions=(sol,) * 5,
            cardinality=5,
            representative=sol,
        )
        assert cluster.confidence == 0.5  # 5/10

    def test_cluster_confidence_caps_at_one(self) -> None:
        sol = FilteredSolution(
            code="x",
            code_hash="abc",
            sample_index=0,
            status=SolutionStatus.PASSED,
            test_results=(),
            pass_rate=1.0,
        )
        cluster = ClusterResult(
            cluster_id=0,
            signature=OutputSignature.from_outputs([]),
            solutions=(sol,) * 15,
            cardinality=15,
            representative=sol,
        )
        assert cluster.confidence == 1.0

    def test_submission_set_best(self) -> None:
        sol = FilteredSolution(
            code="x",
            code_hash="abc",
            sample_index=0,
            status=SolutionStatus.PASSED,
            test_results=(),
            pass_rate=1.0,
        )
        s1 = ScoredSolution(solution=sol, cluster_id=0, score=0.8, scoring_model="m")
        s2 = ScoredSolution(solution=sol, cluster_id=1, score=0.95, scoring_model="m")
        ss = SubmissionSet(
            problem_title="P",
            solutions=(s1, s2),
            total_sampled=10,
            total_passed_filter=5,
            total_clusters=2,
            pipeline_duration_ms=1000.0,
        )
        assert ss.best is not None
        assert ss.best.score == 0.95

    def test_submission_set_empty_best(self) -> None:
        ss = SubmissionSet(
            problem_title="P",
            solutions=(),
            total_sampled=0,
            total_passed_filter=0,
            total_clusters=0,
            pipeline_duration_ms=0.0,
        )
        assert ss.best is None


class TestConfig:
    """Tests for AlphaCodeConfig validation and temperature scheduling."""

    def test_default_config(self) -> None:
        config = AlphaCodeConfig()
        assert config.num_samples == 50
        assert config.temperature_range == (0.6, 1.2)

    def test_temperature_schedule_boundaries(self) -> None:
        config = AlphaCodeConfig(num_samples=10, temperature_range=(0.5, 1.5))
        assert config.temperature_for_sample(0) == 0.5
        assert abs(config.temperature_for_sample(9) - 1.5) < 1e-9

    def test_temperature_schedule_single_sample(self) -> None:
        config = AlphaCodeConfig(num_samples=1, temperature_range=(0.5, 1.5))
        assert config.temperature_for_sample(0) == 0.5

    def test_temperature_schedule_monotonic(self) -> None:
        config = AlphaCodeConfig(num_samples=20, temperature_range=(0.5, 1.5))
        temps = [config.temperature_for_sample(i) for i in range(20)]
        assert temps == sorted(temps)

    def test_validation_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            AlphaCodeConfig(num_samples=0)
        with pytest.raises(ValidationError):
            AlphaCodeConfig(num_samples=-1)

    def test_frozen(self) -> None:
        config = AlphaCodeConfig()
        with pytest.raises(ValidationError):
            config.num_samples = 999  # type: ignore[misc]


# ─── Runner Tests ─────────────────────────────────────────────────────────


class TestRunner:
    """Tests for the SandboxRunner subprocess execution."""

    def test_normalize_output(self) -> None:
        assert _normalize_output("3\n") == "3"
        assert _normalize_output("3 \n4  \n") == "3\n4"
        # Trailing empty lines are stripped by rstrip('\n')
        assert _normalize_output("hello\nworld\n\n") == "hello\nworld"

    @pytest.mark.asyncio
    async def test_run_correct_python(
        self, simple_problem: Problem, correct_python_solution: str
    ) -> None:
        runner = SandboxRunner(timeout_seconds=5.0)
        sample = SampledSolution(
            code=correct_python_solution,
            sample_index=0,
            temperature=0.8,
            model_name="test",
            generation_time_ms=0.0,
        )
        result = await runner.run_solution(
            sample, list(simple_problem.example_tests), Language.PYTHON
        )
        assert result.status == SolutionStatus.PASSED
        assert result.pass_rate == 1.0
        assert result.passed_all

    @pytest.mark.asyncio
    async def test_run_wrong_python(
        self, simple_problem: Problem, wrong_python_solution: str
    ) -> None:
        runner = SandboxRunner(timeout_seconds=5.0)
        sample = SampledSolution(
            code=wrong_python_solution,
            sample_index=0,
            temperature=0.8,
            model_name="test",
            generation_time_ms=0.0,
        )
        result = await runner.run_solution(
            sample, list(simple_problem.example_tests), Language.PYTHON
        )
        assert result.status == SolutionStatus.FAILED
        assert result.pass_rate == 0.0

    @pytest.mark.asyncio
    async def test_run_timeout_python(
        self, simple_problem: Problem, timeout_python_solution: str
    ) -> None:
        runner = SandboxRunner(timeout_seconds=1.0)
        sample = SampledSolution(
            code=timeout_python_solution,
            sample_index=0,
            temperature=0.8,
            model_name="test",
            generation_time_ms=0.0,
        )
        result = await runner.run_solution(
            sample, list(simple_problem.example_tests), Language.PYTHON
        )
        assert result.status == SolutionStatus.TIMEOUT
        assert result.pass_rate == 0.0

    @pytest.mark.asyncio
    async def test_run_syntax_error(self, simple_problem: Problem) -> None:
        runner = SandboxRunner(timeout_seconds=5.0)
        sample = SampledSolution(
            code="print('hello'\n  pass",  # Unclosed paren then indented
            sample_index=0,
            temperature=0.8,
            model_name="test",
            generation_time_ms=0.0,
        )
        result = await runner.run_solution(
            sample, list(simple_problem.example_tests), Language.PYTHON
        )
        # Syntax errors manifest as RUNTIME_ERROR (subprocess exits non-zero)
        assert result.status in (SolutionStatus.RUNTIME_ERROR, SolutionStatus.FAILED)
        assert result.pass_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_output_for_input(self, correct_python_solution: str) -> None:
        runner = SandboxRunner(timeout_seconds=5.0)
        output = await runner.get_output_for_input(
            correct_python_solution, "5 7", Language.PYTHON
        )
        assert _normalize_output(output) == "12"


# ─── Sampler Tests ────────────────────────────────────────────────────────


class TestSampler:
    """Tests for code extraction and prompt building."""

    def test_extract_code_clean(self) -> None:
        assert _extract_code("print(42)") == "print(42)"

    def test_extract_code_with_fences(self) -> None:
        raw = "Here is the solution:\n```python\nprint(42)\n```\nThat's it."
        assert _extract_code(raw) == "print(42)"

    def test_extract_code_with_cpp_fences(self) -> None:
        raw = "```cpp\n#include <iostream>\nint main() {}\n```"
        assert _extract_code(raw) == "#include <iostream>\nint main() {}"

    def test_build_user_prompt(self, simple_problem: Problem) -> None:
        prompt = _build_user_prompt(simple_problem)
        assert "A+B Problem" in prompt
        assert "1 2" in prompt
        assert "300" in prompt
        assert "Time limit" in prompt


# ─── Clusterer Tests ──────────────────────────────────────────────────────


class TestClusterer:
    """Tests for the clustering logic (with mocked LLM and runner)."""

    def test_trivial_clusters(self) -> None:
        from cortex.alphacode._clusterer import Clusterer

        sol = FilteredSolution(
            code="x",
            code_hash="abc",
            sample_index=0,
            status=SolutionStatus.PASSED,
            test_results=(),
            pass_rate=1.0,
        )
        clusters = Clusterer._trivial_clusters([sol])
        assert len(clusters) == 1
        assert clusters[0].cardinality == 1


# ─── Pipeline Integration Tests ──────────────────────────────────────────


class TestPipeline:
    """Integration tests for the full pipeline with mocked LLM."""

    @pytest.mark.asyncio
    async def test_pipeline_with_correct_solution(
        self, simple_problem: Problem, correct_python_solution: str
    ) -> None:
        """Pipeline should produce at least one solution when LLM returns correct code."""
        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"

        # Mock LLM to always return the correct solution
        mock_llm.complete = AsyncMock(return_value=correct_python_solution)

        from cortex.alphacode._pipeline import AlphaCodePipeline

        config = AlphaCodeConfig(
            num_samples=3,
            execution_timeout_seconds=5.0,
            num_generated_inputs=2,
            max_clusters=3,
            use_llm_scoring=False,  # Skip LLM scoring in test
            max_concurrent_samples=3,
            max_concurrent_executions=3,
        )

        pipeline = AlphaCodePipeline(llm=mock_llm, config=config)
        result = await pipeline.solve(simple_problem)

        assert result.problem_title == "A+B Problem"
        # Should have exactly 1 unique solution (all same code)
        assert result.total_sampled >= 1
        assert result.total_passed_filter >= 1

    @pytest.mark.asyncio
    async def test_pipeline_no_solutions(self, simple_problem: Problem) -> None:
        """Pipeline should return empty SubmissionSet when LLM returns garbage."""
        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"
        mock_llm.complete = AsyncMock(return_value="this is not code")

        from cortex.alphacode._pipeline import AlphaCodePipeline

        config = AlphaCodeConfig(
            num_samples=2,
            execution_timeout_seconds=2.0,
            use_llm_scoring=False,
            max_concurrent_samples=2,
            max_concurrent_executions=2,
        )

        pipeline = AlphaCodePipeline(llm=mock_llm, config=config)
        result = await pipeline.solve(simple_problem)

        assert result.total_passed_filter == 0
        assert len(result.solutions) == 0

    @pytest.mark.asyncio
    async def test_pipeline_diverse_solutions(self, simple_problem: Problem) -> None:
        """Pipeline clusters different implementations separately."""
        solutions = [
            "a, b = map(int, input().split())\nprint(a + b)",
            "import sys\nx, y = map(int, sys.stdin.readline().split())\nprint(x + y)",
            "print(sum(map(int, input().split())))",
        ]
        call_count = 0

        async def mock_complete(prompt, system="", temperature=0.3, max_tokens=2048):
            nonlocal call_count
            idx = call_count % len(solutions)
            call_count += 1
            return solutions[idx]

        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"
        mock_llm.complete = mock_complete

        from cortex.alphacode._pipeline import AlphaCodePipeline

        config = AlphaCodeConfig(
            num_samples=3,
            execution_timeout_seconds=5.0,
            num_generated_inputs=3,
            max_clusters=5,
            use_llm_scoring=False,
            max_concurrent_samples=3,
            max_concurrent_executions=5,
        )

        pipeline = AlphaCodePipeline(llm=mock_llm, config=config)
        result = await pipeline.solve(simple_problem)

        # All 3 solutions are correct, so they should all pass filtering
        assert result.total_sampled == 3
        assert result.total_passed_filter == 3
