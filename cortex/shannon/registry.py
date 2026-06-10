# cortex/shannon/registry.py
# [C5-REAL] Exergy-Maximized

from .env.genesis_env import GenesisEnv

ENV_REGISTRY = {"genesis-v1": GenesisEnv}


def make(env_id: str, **kwargs):
    """
    Instantiate a Shannon binary environment by ID, matching Gymnasium syntax.
    """
    if env_id not in ENV_REGISTRY:
        raise ValueError(f"Unknown environment ID: {env_id}")
    return ENV_REGISTRY[env_id](**kwargs)
