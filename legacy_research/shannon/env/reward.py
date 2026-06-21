# cortex/shannon/env/reward.py
# [C5-REAL] Exergy-Maximized


def calculate_step_reward(status: str, steps: int) -> float:
    """
    Standard reward calculation for binary protocol steps.
    """
    if status == "success":
        return 100.0 - steps
    elif status == "invalid_hash":
        return -10.0
    elif status == "invalid_struct":
        return -5.0
    elif status == "buffer_too_small":
        return -2.0
    return -1.0
