# [C5-REAL] Exergy-Maximized
"""Unit tests for the ExergyCostScheduler."""

from babylon60.engine.core.cost_scheduler import ExergyCostScheduler


def test_cost_scheduler_fallback():
    # If policy yaml doesn't exist, we expect it to fallback to defaults
    scheduler = ExergyCostScheduler(policy_path="/nonexistent/path/policy.yaml")

    # IDLE_STATE check
    idle_config = scheduler.determine_state("normal query", {})
    assert idle_config["state"] == "IDLE_STATE"
    assert idle_config["model"] == "3.1 Flash-Lite"

    # CONSTRUCT_STATE check
    construct_config = scheduler.determine_state("crea un nuevo archivo", {})
    assert construct_config["state"] == "CONSTRUCT_STATE"
    assert construct_config["model"] == "3.5 Flash"

    # APEX_STATE check
    apex_config = scheduler.determine_state("PIENSA profundamente", {})
    assert apex_config["state"] == "APEX_STATE"
    assert apex_config["model"] == "3.1 Pro"


def test_cost_scheduler_triggers():
    scheduler = ExergyCostScheduler()  # Loads policy from DEFAULT_POLICY_PATH if it exists

    # Check CONSTRUCT triggers via context
    config = scheduler.determine_state("test", {"ast_diff_size": 100})
    assert config["state"] == "CONSTRUCT_STATE"

    config2 = scheduler.determine_state("test", {"git_status": "dirty"})
    assert config2["state"] == "CONSTRUCT_STATE"

    # Check APEX triggers via context
    config3 = scheduler.determine_state("test", {"system_entropy_spike": True})
    assert config3["state"] == "APEX_STATE"

    config4 = scheduler.determine_state("test", {"target_is_destructive": True})
    assert config4["state"] == "APEX_STATE"


def test_cost_scheduler_interrupts():
    scheduler = ExergyCostScheduler()

    # 1. NMI Triggered
    config = scheduler.determine_state("PIENSA", {})
    assert config["state"] == "APEX_STATE"
    assert config["interrupt_action"] == "FORCE_APEX_STATE"

    # 2. Apoptosis Trigger
    config2 = scheduler.determine_state(
        "test", {"dead_code_ratio": 0.5, "complexity_penalty": 12.0}
    )
    assert config2["state"] == "INTERRUPT"
    assert config2["action"] == "KILL_PROCESS && PURGE_MEMORY"

    # 3. Thermodynamic Bailout
    config3 = scheduler.determine_state("test", {"loop_count": 4, "resolution_status": False})
    assert config3["state"] == "IDLE_STATE"
    assert config3["interrupt_action"] == "DEGRADE_TO_IDLE && REQUEST_USER_OVERRIDE"
