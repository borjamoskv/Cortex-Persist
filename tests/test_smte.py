# [C5-REAL] Exergy-Maximized
"""
Tests for Self-Modifying Topology Engine (SMTE).
Aligned with the consolidated cortex/engine/smte/ module.

Reality Level: C5-REAL
"""

import os
import sys
import json
import tempfile
import pytest
import ast
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root and cortex-core to sys.path dynamically
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "cortex-core") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "cortex-core"))

from cortex.engine.smte.parser import AgentASTParser
from cortex.engine.smte.analyzer import calculate_ast_complexity, estimate_dead_code_ratio
from cortex.engine.smte.exergy import ExergyMonitor, evaluate_module_exergy
from cortex.engine.smte.ouroboros_compiler import OuroborosCompiler
from cortex.engine.smte.weismann_barrier import enforce_weismann_barrier
from cortex.engine.smte.llm_mutator import llm_driven_mutator


# Sample code for testing AST parsing and analysis
SAMPLE_CODE = """
def hello_world():
    print("Hello, world!")

async def async_fn(x):
    if x > 10:
        return True
    else:
        return False

class MyClass:
    def method_one(self):
        pass

    async def method_two(self):
        try:
            return 1
        except Exception:
            return 0
"""

COMPLEX_SAMPLE_CODE = """
def complex_fn(x, y):
    val = 1
    if x:
        for i in range(10):
            if y:
                val += 1
            else:
                val -= 1
    while val < 5:
        val += 1
    return val
"""

DEAD_CODE_SAMPLE_CODE = """
def empty_fn():
    pass

def unreachable_fn():
    return 10
    print("unreachable")
    x = 20
"""


@pytest.fixture
def temp_source_file():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as f:
        f.write(SAMPLE_CODE)
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestAgentASTParser:
    def test_load_and_extract_topology(self, temp_source_file):
        parser = AgentASTParser(temp_source_file)
        topology = parser.get_topology()

        # Verify classes
        assert len(topology["classes"]) == 1
        assert topology["classes"][0]["name"] == "MyClass"
        assert "method_one" in topology["classes"][0]["methods"]
        assert "method_two" in topology["classes"][0]["methods"]

        # Verify top-level functions
        func_names = [f["name"] for f in topology["functions"]]
        assert "hello_world" in func_names
        assert "async_fn" in func_names
        assert len(topology["functions"]) == 2

    def test_apply_mutation(self, temp_source_file):
        parser = AgentASTParser(temp_source_file)

        # Mutation that appends an attribute check or dummy node to a function
        def mock_mutator(tree):
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "hello_world":
                    # add a dummy pass statement
                    node.body.append(ast.Pass())
                    return True
            return False

        success = parser.apply_mutation(mock_mutator)
        assert success is True

        # Verify crystallization
        mutated_code = parser.crystallize()
        assert mutated_code is not None

        # Reload to verify persistence
        parser2 = AgentASTParser(temp_source_file)
        topology = parser2.get_topology()
        func_names = [f["name"] for f in topology["functions"]]
        assert "hello_world" in func_names


class TestSMTEAnalyzer:
    def test_calculate_ast_complexity(self):
        comp = calculate_ast_complexity(COMPLEX_SAMPLE_CODE)
        assert comp == 5.0

    def test_calculate_ast_complexity_syntax_error(self):
        comp = calculate_ast_complexity("invalid python code {")
        assert comp == 10.0

    def test_estimate_dead_code_ratio(self):
        ratio = estimate_dead_code_ratio(DEAD_CODE_SAMPLE_CODE)
        assert ratio > 0.0
        assert ratio <= 1.0


class TestExergyMonitor:
    def test_set_l_epi_metrics_and_calculate(self):
        # Set circuit_breaker_threshold high enough to prevent tripping
        monitor = ExergyMonitor("test_target", circuit_breaker_threshold=30.0)
        monitor.set_l_epi_metrics(ast_complexity=5.0, empirical_usage=2.0, dead_code_ratio=0.3)

        monitor.start_transaction()
        monitor.end_transaction(success=True)

        metrics = monitor.calculate_metrics()
        assert metrics["target"] == "test_target"
        assert metrics["status"] == "C5-REAL"
        assert "entropy" in metrics
        assert "exergy" in metrics
        assert metrics["dead_code_ratio"] == 0.3
        # limerence_penalty = (5.0 / 2.0) * 10.0 = 25.0
        assert metrics["limerence_penalty"] == 25.0

    def test_circuit_breaker_tripped(self):
        from cortex.engine.smte.exergy import CircuitBreakerTripped

        monitor = ExergyMonitor("test_breaker", circuit_breaker_threshold=20.0)
        # 5.0 / 2.0 * 10.0 = 25.0 > 20.0
        monitor.set_l_epi_metrics(ast_complexity=5.0, empirical_usage=2.0, dead_code_ratio=0.3)

        monitor.start_transaction()
        monitor.end_transaction(success=True)

        with pytest.raises(CircuitBreakerTripped) as exc_info:
            monitor.calculate_metrics()
        assert "Circuit breaker tripped" in str(exc_info.value)

    def test_evaluate_module_exergy(self):
        results = [
            {"status": "C5-REAL", "latency": 0.1},
            {"status": "error", "latency": 0.5},
            {"status": "C5-REAL", "latency": 1.2},  # latency penalty +0.2
        ]
        avg_entropy = evaluate_module_exergy(results)
        # expected: (0.0 + 1.0 + 0.2) / 3 = 0.4
        assert abs(avg_entropy - 0.4) < 1e-6


class TestWeismannBarrier:
    def test_enforce_weismann_barrier_success(self, temp_source_file):
        # A mutator that changes code to valid Python
        def mutator(filepath):
            with open(filepath, "w") as f:
                f.write("x = 10\n")
            return True

        success = enforce_weismann_barrier(temp_source_file, mutator)
        assert success is True

        with open(temp_source_file) as f:
            content = f.read()
        assert content == "x = 10\n"

    def test_enforce_weismann_barrier_syntax_failure(self, temp_source_file):
        # A mutator that outputs invalid syntax
        def mutator(filepath):
            with open(filepath, "w") as f:
                f.write("invalid syntax === \n")
            return True

        success = enforce_weismann_barrier(temp_source_file, mutator)
        assert success is False

        # Original should be untouched
        with open(temp_source_file) as f:
            content = f.read()
        assert "hello_world" in content

    def test_enforce_weismann_barrier_none_callback(self, temp_source_file):
        # Passing None callback should evaluate as True mutation check
        success = enforce_weismann_barrier(temp_source_file, None)
        assert success is True


class TestOuroborosCompiler:
    def test_analyze_limerence(self):
        compiler = OuroborosCompiler()
        analysis = compiler.analyze_limerence(SAMPLE_CODE)
        assert "complexity" in analysis
        assert "dead_code_ratio" in analysis
        assert "limerence_penalty" in analysis
        assert "is_limerent" in analysis
        assert "must_amputate" in analysis

    @pytest.mark.asyncio
    @patch("cortex.engine.smte.ouroboros_compiler.call_qwen_mutator")
    @patch("cortex.engine.CortexEngine")
    async def test_compile_entity_success(self, mock_engine_cls, mock_qwen, temp_source_file):
        # Mock CortexEngine store method
        mock_engine = MagicMock()
        mock_engine.store = AsyncMock()
        mock_engine_cls.return_value = mock_engine

        compiler = OuroborosCompiler()
        compiler._engine = mock_engine

        # Mock Qwen response with valid python code
        mock_qwen.return_value = "x = 42\n"

        result = await compiler.compile_entity(temp_source_file)
        assert result is True

        # Verify file content updated
        with open(temp_source_file) as f:
            content = f.read()
        assert content == "x = 42\n"

        mock_engine.store.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("cortex.engine.CortexEngine")
    async def test_compile_entity_amputation(self, mock_engine_cls, temp_source_file):
        mock_engine = MagicMock()
        mock_engine.store = AsyncMock()
        mock_engine_cls.return_value = mock_engine

        compiler = OuroborosCompiler()
        compiler._engine = mock_engine

        # Target high dead code and high complexity to force amputation
        with patch.object(compiler, "analyze_limerence") as mock_analyze:
            mock_analyze.return_value = {
                "complexity": 5.0,
                "dead_code_ratio": 0.5,  # > 0.4
                "limerence_penalty": 15.0,  # > 10.0
                "is_limerent": True,
                "must_amputate": True,
            }

            result = await compiler.compile_entity(temp_source_file)
            assert result is True
            # File should be unlinked/deleted by amputation
            assert not os.path.exists(temp_source_file)
            mock_engine.store.assert_awaited_once()


class TestLLMDrivenMutator:
    @patch("cortex.engine.smte.llm_mutator.call_qwen_mutator")
    def test_llm_driven_mutator_success(self, mock_qwen, temp_source_file):
        parser = AgentASTParser(temp_source_file)

        # Qwen returns valid updated python code with a functional statement
        mock_qwen.return_value = SAMPLE_CODE + "\nEXTRA_VAR = 999\n"

        success = llm_driven_mutator(parser)
        assert success is True
        assert "EXTRA_VAR = 999" in ast.unparse(parser.tree)
