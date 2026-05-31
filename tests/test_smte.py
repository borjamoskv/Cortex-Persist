"""
Tests for Self-Modifying Topology Engine (SMTE).

Reality Level: C5-REAL
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from engine.smte.parser import CortexASTParser
from engine.smte.analyzer import calculate_ast_complexity, estimate_dead_code_ratio
from engine.smte.exergy import ExergyMonitor
from engine.smte.ouroboros import OuroborosLoop


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


class TestCortexASTParser:
    def test_load_and_extract_functions(self, temp_source_file):
        parser = CortexASTParser(temp_source_file)
        funcs = parser.extract_functions()
        func_names = [f["name"] for f in funcs]
        assert "hello_world" in func_names
        assert "async_fn" in func_names
        assert "method_one" in func_names
        assert "method_two" in func_names
        assert len(funcs) == 4

    def test_extract_classes(self, temp_source_file):
        parser = CortexASTParser(temp_source_file)
        classes = parser.extract_classes()
        assert len(classes) == 1
        assert classes[0]["name"] == "MyClass"
        assert "method_one" in classes[0]["methods"]
        assert "method_two" in classes[0]["methods"]

    def test_get_source_segment(self, temp_source_file):
        parser = CortexASTParser(temp_source_file)
        # Find async_fn start and end lines
        funcs = parser.extract_functions()
        async_fn_info = next(f for f in funcs if f["name"] == "async_fn")
        segment = parser.get_source_segment(async_fn_info["lineno"], async_fn_info["end_lineno"])
        assert "async def async_fn(x):" in segment
        assert "return False" in segment

    def test_inject_mutation_and_save(self, temp_source_file):
        parser = CortexASTParser(temp_source_file)
        original = "print(\"Hello, world!\")"
        mutated = "print(\"Hello, mutated world!\")"
        new_source = parser.inject_mutation(original, mutated)
        assert mutated in new_source
        assert original not in new_source
        parser.save()

        # Reload to verify persistence
        parser2 = CortexASTParser(temp_source_file)
        assert mutated in parser2.source_code
        assert original not in parser2.source_code

    def test_invalid_syntax_mutation_raises(self, temp_source_file):
        parser = CortexASTParser(temp_source_file)
        with pytest.raises(ValueError, match="invalid syntax"):
            parser.inject_mutation("print(\"Hello, world!\")", "def invalid syntax :(")


class TestSMTEAnalyzer:
    def test_calculate_ast_complexity(self):
        # Base complexity is 1.0. branches: if (1), for (1), if (1) inside for, while (1). Total branch count = 4. Complexity = 5.0
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
        monitor = ExergyMonitor("test_target")
        monitor.set_l_epi_metrics(ast_complexity=5.0, empirical_usage=2.0, dead_code_ratio=0.3)
        
        monitor.start_transaction()
        # simulate some work
        monitor.end_transaction(success=True)
        
        metrics = monitor.calculate_metrics()
        assert metrics["target"] == "test_target"
        assert metrics["status"] == "C5-REAL"
        assert "entropy" in metrics
        assert "exergy" in metrics
        assert metrics["dead_code_ratio"] == 0.3
        # limerence_penalty = (5.0 / 2.0) * 10.0 = 25.0
        assert metrics["limerence_penalty"] == 25.0


class TestOuroborosLoop:
    def test_transcribe(self, temp_source_file):
        loop = OuroborosLoop(temp_source_file)
        funcs = loop.transcribe()
        assert len(funcs) == 4

    @patch("cortex.extensions.mcp.claude_tool.run_claude_query")
    def test_propose_mutation_success(self, mock_query, temp_source_file):
        loop = OuroborosLoop(temp_source_file)
        
        # Mock successful Claude MCP response
        mock_response = {
            "status": "C5-REAL",
            "model": "claude-3-opus",
            "response": "def hello_world():\n    print('Hello from mutation!')"
        }
        mock_query.return_value = json.dumps(mock_response)
        
        exergy_metrics = {
            "entropy": 0.5,
            "latency": 0.1,
            "status": "C5-REAL",
            "dead_code_ratio": 0.1,
            "limerence_penalty": 2.0
        }
        
        mutated_code = loop.propose_mutation("hello_world", exergy_metrics)
        assert "Hello from mutation!" in mutated_code
        mock_query.assert_called_once()

    def test_propose_mutation_l_epi_guard_purge(self, temp_source_file):
        loop = OuroborosLoop(temp_source_file)
        
        exergy_metrics = {
            "entropy": 1.0,
            "latency": 1.5,
            "status": "error",
            "dead_code_ratio": 0.5,  # > 0.4
            "limerence_penalty": 15.0  # > 10.0
        }
        
        # Should trigger L-EPI Guard automatic amputation (returns empty string)
        mutated_code = loop.propose_mutation("hello_world", exergy_metrics)
        assert mutated_code == ""

    def test_mutate_and_integrate(self, temp_source_file):
        loop = OuroborosLoop(temp_source_file)
        
        new_hello = "def hello_world():\n    return 'mutated!'"
        loop.mutate("hello_world", new_hello)
        loop.integrate()
        
        # Read back from file
        with open(temp_source_file, "r") as f:
            content = f.read()
        assert "mutated!" in content

    @patch("subprocess.run")
    def test_validate_in_sandbox_success(self, mock_run, temp_source_file):
        loop = OuroborosLoop(temp_source_file)
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        assert loop.validate_in_sandbox() is True

    @patch("subprocess.run")
    def test_validate_in_sandbox_failure(self, mock_run, temp_source_file):
        loop = OuroborosLoop(temp_source_file)
        
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "Test failure detail"
        mock_run.return_value = mock_proc
        
        assert loop.validate_in_sandbox() is False

    def test_mitosis(self, temp_source_file):
        loop = OuroborosLoop(temp_source_file)
        # Verify mitosis doesn't raise if module isn't loaded in sys.modules
        loop.mitosis("some_random_module_that_does_not_exist")
