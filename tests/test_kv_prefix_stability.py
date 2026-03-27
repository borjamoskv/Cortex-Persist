"""AX-042 KV-Aware Routing — Prefix Stability Tests.

Asserts that system_instruction prefixes are deterministic
(no dynamic data injected), enabling vLLM/Dynamo APC cache hits.
"""

from __future__ import annotations

import os

os.environ.setdefault("CORTEX_TESTING", "1")


class TestTranslateSystemInstruction:
    """_build_system_instruction returns identical output regardless of context."""

    def test_returns_static_string(self):
        from cortex.routes.translate import _build_system_instruction

        a = _build_system_instruction()
        b = _build_system_instruction()
        assert a == b

    def test_no_context_parameter(self):
        """Signature must not accept context (AX-042 enforcement)."""
        import inspect

        from cortex.routes.translate import _build_system_instruction

        sig = inspect.signature(_build_system_instruction)
        assert len(sig.parameters) == 0, (
            f"_build_system_instruction must take no params, "
            f"got: {list(sig.parameters)}"
        )

    def test_contains_omni_translate(self):
        from cortex.routes.translate import _build_system_instruction

        assert "OMNI-TRANSLATE" in _build_system_instruction()


class TestDeepThinkPrefix:
    """orchestrator_deep_think uses a static system_instruction."""

    def test_system_instruction_is_static_string(self):
        """The CortexPrompt system_instruction must not contain
        agent-specific dynamic data."""
        import ast

        src_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "cortex",
            "extensions",
            "swarm",
            "orchestrator_deep_think.py",
        )
        with open(src_path) as f:
            tree = ast.parse(f.read())

        # Find CortexPrompt(...) call and check system_instruction
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "CortexPrompt"
            ):
                for kw in node.keywords:
                    if kw.arg == "system_instruction":
                        # Must NOT be an f-string (JoinedStr)
                        assert not isinstance(
                            kw.value, ast.JoinedStr
                        ), (
                            "system_instruction uses f-string "
                            "(AX-042 violation)"
                        )
                        break


class TestLLMActuatorPrefix:
    """LLMActuator system_instruction is instance-deterministic."""

    def test_no_context_in_system_instruction(self):
        """system_instruction must not reference context dict."""
        import ast

        src_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "cortex",
            "swarm",
            "actuators",
            "llm.py",
        )
        with open(src_path) as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "CortexPrompt"
            ):
                for kw in node.keywords:
                    if kw.arg == "system_instruction":
                        # Check the f-string doesn't contain
                        # 'context' or 'instructions'
                        segment = ast.get_source_segment(
                            source, kw.value
                        )
                        if segment:
                            assert "context" not in segment.lower(), (
                                "system_instruction references "
                                "'context' (AX-042 violation)"
                            )
                        break
