# [C5-REAL] Exergy-Maximized — FPU Eradication Test Suite
# Author: Borja Moskv (borjamoskv)
"""Tests for BABYLON-60 float eradication infrastructure."""

import ast

import pytest

from cortex.engine.ast_validator import validate_ast
from legacy_research.math.fpu_interceptor import FPUFirewall, FPUViolationError, no_float


# ─── FPUFirewall Tests ───────────────────────────────────────────


class TestFPUFirewall:
    def test_guard_rejects_float_args(self):
        with pytest.raises(FPUViolationError, match="FPU VIOLATION"):
            FPUFirewall.guard_args("test_func", x=3.14)

    def test_guard_accepts_int(self):
        FPUFirewall.guard_args("test_func", x=42, y=100)

    def test_guard_accepts_none(self):
        FPUFirewall.guard_args("test_func", x=None)

    def test_guard_positional_rejects_float(self):
        with pytest.raises(FPUViolationError, match="arg\\[1\\]"):
            FPUFirewall.guard_positional("test_func", (10, 3.14, 20))

    def test_guard_positional_accepts_ints(self):
        FPUFirewall.guard_positional("test_func", (10, 20, 30))

    def test_guard_return_rejects_float(self):
        with pytest.raises(FPUViolationError, match="returned"):
            FPUFirewall.guard_return(2.718, "compute")

    def test_guard_return_passes_int(self):
        result = FPUFirewall.guard_return(42, "compute")
        assert result == 42

    def test_guard_dict_rejects_float_value(self):
        with pytest.raises(FPUViolationError, match="score"):
            FPUFirewall.guard_dict({"name": "test", "score": 0.95}, "metadata")

    def test_guard_dict_accepts_int_values(self):
        FPUFirewall.guard_dict({"name": "test", "count": 42}, "metadata")

    def test_guard_iterable_rejects_float(self):
        with pytest.raises(FPUViolationError, match="\\[2\\]"):
            FPUFirewall.guard_iterable([1, 2, 3.0, 4], "distances")


# ─── @no_float Decorator Tests ───────────────────────────────────


class TestNoFloatDecorator:
    def test_decorator_blocks_float_arg(self):
        @no_float
        def add(a, b):
            return a + b

        with pytest.raises(FPUViolationError):
            add(1, 2.0)

    def test_decorator_blocks_float_kwarg(self):
        @no_float
        def add(a, b=0):
            return a + b

        with pytest.raises(FPUViolationError):
            add(1, b=2.5)

    def test_decorator_blocks_float_return(self):
        @no_float
        def bad_compute(x):
            return x / 2  # Python 3 true division returns float

        with pytest.raises(FPUViolationError):
            bad_compute(5)

    def test_decorator_passes_int_roundtrip(self):
        @no_float
        def add(a, b):
            return a + b

        assert add(10, 20) == 30

    def test_decorator_preserves_function_name(self):
        @no_float
        def my_function():
            return 0

        assert my_function.__name__ == "my_function"


# ─── AST Validator Extended Tests ────────────────────────────────


class TestASTFloatDetection:
    def test_catches_float_literal(self):
        code = "x = 3.14"
        errors = validate_ast(code, "test.py")
        assert any("Float literal" in msg for _, msg in errors)

    def test_catches_float_annotation(self):
        code = "def compute(x: float) -> int:\n    return int(x)"
        errors = validate_ast(code, "test.py")
        assert any("Float annotation" in msg for _, msg in errors)

    def test_catches_float_return_annotation(self):
        code = "def compute(x: int) -> float:\n    return 1.0"
        errors = validate_ast(code, "test.py")
        assert any("Float return annotation" in msg or "Float literal" in msg for _, msg in errors)

    def test_catches_float_conversion(self):
        code = "x = float(42)"
        errors = validate_ast(code, "test.py")
        assert any("float() conversion" in msg for _, msg in errors)

    def test_catches_true_division(self):
        code = "x = a / b"
        errors = validate_ast(code, "test.py")
        assert any("True division" in msg or "division" in msg.lower() for _, msg in errors)

    def test_passes_integer_floor_division(self):
        code = "x = a // b"
        errors = validate_ast(code, "test.py")
        # Floor division should NOT trigger float warnings
        assert not any("division" in msg.lower() for _, msg in errors)

    def test_passes_pure_integer_code(self):
        code = "x = 42\ny = x + 10\nz = x // 3"
        errors = validate_ast(code, "test.py")
        assert len(errors) == 0

    def test_catches_optional_float(self):
        code = "from typing import Optional\ndef f(x: Optional[float]) -> None:\n    pass"
        errors = validate_ast(code, "test.py")
        assert any("Float annotation" in msg for _, msg in errors)
