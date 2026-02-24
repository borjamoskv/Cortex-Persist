"""Tests for cortex.sandbox — AST Sandbox."""

from __future__ import annotations

import pytest

from cortex.utils.sandbox import ASTSandbox, SandboxVerdict


@pytest.fixture
def sandbox() -> ASTSandbox:
    return ASTSandbox()


class TestSandboxVerdict:
    def test_safe_repr(self):
        v = SandboxVerdict(is_safe=True, node_count=5)
        assert "SAFE" in repr(v)

    def test_unsafe_repr(self):
        v = SandboxVerdict(is_safe=False, violations=("bad",))
        assert "UNSAFE" in repr(v)


class TestValidateSafeCode:
    def test_simple_assignment(self, sandbox: ASTSandbox):
        v = sandbox.validate("x = 42")
        assert v.is_safe is True
        assert v.node_count > 0

    def test_arithmetic(self, sandbox: ASTSandbox):
        v = sandbox.validate("result = (2 + 3) * 10 - 1")
        assert v.is_safe is True

    def test_list_comprehension(self, sandbox: ASTSandbox):
        v = sandbox.validate("squares = [x**2 for x in range(10)]")
        assert v.is_safe is True

    def test_function_def(self, sandbox: ASTSandbox):
        code = "def add(a, b):\n    return a + b\nresult = add(2, 3)"
        v = sandbox.validate(code)
        assert v.is_safe is True

    def test_if_else(self, sandbox: ASTSandbox):
        code = "x = 10\nif x > 5:\n    y = 'big'\nelse:\n    y = 'small'"
        v = sandbox.validate(code)
        assert v.is_safe is True

    def test_for_loop(self, sandbox: ASTSandbox):
        v = sandbox.validate("total = sum(i for i in range(10))")
        assert v.is_safe is True

    def test_lambda(self, sandbox: ASTSandbox):
        v = sandbox.validate("fn = lambda x: x * 2")
        assert v.is_safe is True

    def test_fstring(self, sandbox: ASTSandbox):
        v = sandbox.validate("name = 'world'\ngreeting = f'hello {name}'")
        assert v.is_safe is True


class TestValidateUnsafeCode:
    def test_import_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("import os")
        assert v.is_safe is False
        assert any("Import" in viol for viol in v.violations)

    def test_from_import_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("from pathlib import Path")
        assert v.is_safe is False

    def test_exec_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("exec('print(1)')")
        assert v.is_safe is False
        assert any("exec" in viol for viol in v.violations)

    def test_eval_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("eval('1+1')")
        assert v.is_safe is False

    def test_open_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("f = open('/etc/passwd')")
        assert v.is_safe is False

    def test_dunder_class_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("x = ''.__class__")
        assert v.is_safe is False
        assert any("__class__" in viol for viol in v.violations)

    def test_dunder_subclasses_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("x = object.__subclasses__()")
        assert v.is_safe is False

    def test_dynamic_import_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("__import__('os')")
        assert v.is_safe is False

    def test_class_def_blocked(self, sandbox: ASTSandbox):
        v = sandbox.validate("class Foo:\n    pass")
        assert v.is_safe is False
        assert any("ClassDef" in viol for viol in v.violations)

    def test_syntax_error(self, sandbox: ASTSandbox):
        v = sandbox.validate("def (")
        assert v.is_safe is False
        assert any("SyntaxError" in viol for viol in v.violations)


class TestValidateLimits:
    def test_max_nodes(self):
        sandbox = ASTSandbox(max_nodes=5)
        code = "a=1\nb=2\nc=3\nd=4\ne=5\nf=6\ng=7\nh=8\ni=9\nj=10"
        v = sandbox.validate(code)
        assert v.is_safe is False
        assert any("max node count" in viol for viol in v.violations)

    def test_max_depth(self):
        sandbox = ASTSandbox(max_depth=3)
        code = "if True:\n  if True:\n    if True:\n      if True:\n        x = 1"
        v = sandbox.validate(code)
        assert v.is_safe is False
        assert any("depth" in viol for viol in v.violations)


class TestSafeExec:
    def test_simple_exec(self, sandbox: ASTSandbox):
        result = sandbox.safe_exec("x = 2 + 3\nresult = x * 10")
        assert result.success is True
        assert result.output["result"] == 50
        assert result.output["x"] == 5

    def test_print_capture(self, sandbox: ASTSandbox):
        result = sandbox.safe_exec("print('hello')")
        assert result.success is True
        assert "hello" in result.stdout

    def test_function_execution(self, sandbox: ASTSandbox):
        code = (
            "def fib(n):\n    if n < 2: return n\n    return fib(n-1) + fib(n-2)\nresult = fib(10)"
        )
        result = sandbox.safe_exec(code)
        assert result.success is True
        assert result.output["result"] == 55

    def test_rejected_code(self, sandbox: ASTSandbox):
        result = sandbox.safe_exec("import os")
        assert result.success is False
        assert "Validation failed" in result.error

    def test_runtime_error(self, sandbox: ASTSandbox):
        result = sandbox.safe_exec("x = 1 / 0")
        assert result.success is False
        assert "ZeroDivisionError" in result.error

    def test_duration_tracked(self, sandbox: ASTSandbox):
        result = sandbox.safe_exec("x = sum(range(1000))")
        assert result.success is True
        assert result.duration_ms > 0

    def test_namespace_isolation(self, sandbox: ASTSandbox):
        """Internal names should not leak to output."""
        result = sandbox.safe_exec("x = 42")
        assert "__builtins__" not in result.output
        assert all(not k.startswith("_") for k in result.output)
