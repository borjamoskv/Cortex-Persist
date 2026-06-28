"""
[C5-REAL] Exergy-Maximized
Architecture Governance Test: CLI Lazy Loading
"""

import sys
import subprocess


def test_cli_lazy_loading_invariant():
    """
    Ensure that importing cortex.cli.main does NOT eagerly load the subcommands.
    Eager loading destroys CLI startup performance (exergy drain).
    """
    # Launch a clean Python subprocess that imports cortex.cli.main and prints out
    # all loaded modules that end with '_cmds'.
    code = (
        "import sys\n"
        "import cortex.cli.main\n"
        "loaded_cmds = [m for m in sys.modules if m.startswith('cortex.cli.') and m.endswith('_cmds')]\n"
        "print(','.join(loaded_cmds))\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    loaded_cmds_str = result.stdout.strip()
    loaded_cmds = loaded_cmds_str.split(",") if loaded_cmds_str else []

    assert not loaded_cmds, (
        f"CLI Governance Failure: Eager imports detected during startup: {loaded_cmds}. This degrades startup time."
    )


def test_cli_lazy_loader_works():
    """
    Ensure that accessing a command triggers the lazy load successfully.
    """
    code = (
        "import sys\n"
        "import cortex.cli.main\n"
        "cmd = cortex.cli.main.cli.get_command(None, 'agent')\n"
        "loaded_cmds = [m for m in sys.modules if m.startswith('cortex.cli.') and m.endswith('_cmds')]\n"
        "print(','.join(loaded_cmds))\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    loaded_cmds_str = result.stdout.strip()
    loaded_cmds = loaded_cmds_str.split(",") if loaded_cmds_str else []

    assert len(loaded_cmds) > 0, "Failed to lazy load the commands upon access."
    assert "cortex.cli.agent_cmds" in loaded_cmds, "The specific agent_cmds module was not loaded."
