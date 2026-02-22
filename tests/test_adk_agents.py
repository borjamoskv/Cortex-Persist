"""Tests for CORTEX ADK Agent Definitions.

Tests agent creation, tool registration, and configuration
without requiring Google ADK or a Gemini API key.
"""

import pytest


class TestADKModuleImport:
    """Test the ADK module can be imported."""

    def test_adk_package_import(self):
        """ADK package should be importable."""
        import cortex.adk  # noqa: F401

    def test_tools_module_import(self):
        """Tools module should be importable."""
        from cortex.adk import tools as adk_tools

        assert hasattr(adk_tools, "adk_store")
        assert hasattr(adk_tools, "adk_search")
        assert hasattr(adk_tools, "adk_status")
        assert hasattr(adk_tools, "adk_ledger_verify")
        assert hasattr(adk_tools, "adk_deprecate")
        assert hasattr(adk_tools, "ALL_TOOLS")

    def test_all_tools_list(self):
        """ALL_TOOLS should contain all 4 tool functions."""
        from cortex.adk.tools import ALL_TOOLS

        assert len(ALL_TOOLS) == 5
        names = [f.__name__ for f in ALL_TOOLS]
        assert "adk_store" in names
        assert "adk_search" in names
        assert "adk_status" in names
        assert "adk_ledger_verify" in names
        assert "adk_deprecate" in names

    def test_agents_module_import(self):
        """Agents module should be importable."""
        from cortex.adk import agents as adk_agents

        assert hasattr(adk_agents, "create_memory_agent")
        assert hasattr(adk_agents, "create_analyst_agent")
        assert hasattr(adk_agents, "create_guardian_agent")
        assert hasattr(adk_agents, "create_cortex_swarm")
        assert hasattr(adk_agents, "is_adk_available")

    def test_runner_module_import(self):
        """Runner module should be importable."""
        from cortex.adk import runner as adk_runner

        assert hasattr(adk_runner, "main")
        assert hasattr(adk_runner, "run_cli")


class TestADKTools:
    """Test ADK tool function signatures and docstrings."""

    def test_adk_store_signature(self):
        """adk_store should accept expected parameters."""
        import inspect

        from cortex.adk.tools import adk_store

        sig = inspect.signature(adk_store)
        params = list(sig.parameters.keys())
        assert "project" in params
        assert "content" in params
        assert "fact_type" in params
        assert "tags" in params
        assert "source" in params

    def test_adk_search_signature(self):
        """adk_search should accept expected parameters."""
        import inspect

        from cortex.adk.tools import adk_search

        sig = inspect.signature(adk_search)
        params = list(sig.parameters.keys())
        assert "query" in params
        assert "project" in params
        assert "top_k" in params

    def test_adk_status_signature(self):
        """adk_status should accept no parameters."""
        import inspect

        from cortex.adk.tools import adk_status

        sig = inspect.signature(adk_status)
        assert len(sig.parameters) == 0

    def test_adk_ledger_verify_signature(self):
        """adk_ledger_verify should accept no parameters."""
        import inspect

        from cortex.adk.tools import adk_ledger_verify

        sig = inspect.signature(adk_ledger_verify)
        assert len(sig.parameters) == 0

    def test_tools_have_docstrings(self):
        """All ADK tools should have proper docstrings."""
        from cortex.adk.tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            assert tool.__doc__, f"{tool.__name__} missing docstring"
            assert len(tool.__doc__) > 20, f"{tool.__name__} docstring too short"

    def test_tools_return_dict(self):
        """All tools should have dict return type annotation."""
        import inspect

        from cortex.adk.tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            sig = inspect.signature(tool)
            ret = sig.return_annotation
            assert ret is dict or ret == "dict", (
                f"{tool.__name__} should return dict, got {ret}"
            )

    def test_adk_deprecate_signature(self):
        """adk_deprecate should accept expected parameters."""
        import inspect

        from cortex.adk.tools import adk_deprecate

        sig = inspect.signature(adk_deprecate)
        params = list(sig.parameters.keys())
        assert "fact_id" in params
        assert "reason" in params


class TestADKAgentCreation:
    """Test agent creation (skip if ADK not installed)."""

    def test_adk_availability_flag(self):
        """is_adk_available should return a bool."""
        from cortex.adk.agents import is_adk_available

        assert isinstance(is_adk_available(), bool)

    def test_create_memory_agent_without_adk(self):
        """If ADK is not installed, create_memory_agent should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_memory_agent

                create_memory_agent()
        else:
            pytest.skip("ADK is installed")

    def test_create_analyst_agent_without_adk(self):
        """If ADK is not installed, create_analyst_agent should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_analyst_agent

                create_analyst_agent()
        else:
            pytest.skip("ADK is installed")

    def test_create_guardian_agent_without_adk(self):
        """If ADK is not installed, create_guardian_agent should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_guardian_agent

                create_guardian_agent()
        else:
            pytest.skip("ADK is installed")

    def test_create_swarm_without_adk(self):
        """If ADK is not installed, create_cortex_swarm should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_cortex_swarm

                create_cortex_swarm()
        else:
            pytest.skip("ADK is installed")
