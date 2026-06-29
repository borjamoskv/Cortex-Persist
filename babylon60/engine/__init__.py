# CORTEX ENGINE FACADE
# Auto-generated to maintain compatibility after structural mitosis.

_SWARM_MODULES = {
    "agent_mixin",
    "aleph_omega",
    "auth",
    "auth_gateway",
    "autocurative_agent",
    "autopoietic_agent",
    "enrichment_worker",
    "entropy_daemon",
    "exergy_agent",
    "exergy_daemon",
    "legion",
    "legion_vectors",
    "legion_vectors_plan",
    "nemesis_agent",
    "omega_daemon",
    "phoenix_omega",
    "squadrons",
    "swarm_10k",
    "test_autopoietic_agent",
    "trust_registry",
}

_DEFERRED_ATTRIBUTES = {
    "AsyncCortexEngine": ".core.cortex_engine",
    "CortexEngine": ".core.cortex_engine",
}

def __getattr__(name: str):
    if name in _SWARM_MODULES:
        import importlib
        return importlib.import_module(f"cortex.swarm.{name}")
    if name in _DEFERRED_ATTRIBUTES:
        import importlib
        mod = importlib.import_module(_DEFERRED_ATTRIBUTES[name], __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__():
    return sorted(list(globals().keys()) + list(_SWARM_MODULES) + list(_DEFERRED_ATTRIBUTES.keys()))


from .core import (
    _engine_connection,
    _engine_delegates,
    bifurcation_engine,
    context_cache,
    distributed_ledger,
    embedding_engine,
    engine,
    evolution_engine,
    evolution_ledger,
    fact_store_core,
    memory_mixin,
    mutation_engine,
    physics,
    rollback_engine,
    runtime_kernel,
    snapshots,
    store_mixin,
    store_mutation,
    store_quarantine_mixin,
    store_validation,
    store_validators,
    tips,
    tuning_store,
    ultrathink_physics,
)
from .evo import (
    _autocurative_config,
    _autocurative_helper,
    _autocurative_state,
    _autopoietic_helper,
    _autopoietic_state,
    _genome_mutator,
    _genome_tree_helper,
    _genome_types,
    _mutation_projectors,
    autopoiesis,
    decalcifier,
    evaporator,
    evolution_metrics,
    evolution_types,
    genome,
    growth,
    healing_stack,
    reaper,
    repair_strategies,
)
from .flow import (
    arbiter_bridge,
    bridge_guard,
    cascade_router,
    causal_scheduler,
    causality,
    causality_models,
    checkpoint,
    consensus,
    encb_router,
    execution_ledger,
    guard_adapters,
    guard_integration_patch,
    guard_pipeline,
    lock,
    rim_latent_blocks,
    saga_protocol,
    storage_guard,
)
from .meta import (
    _autopoietic_oracle,
    cognitive,
    cognitive_arbiter,
    forgetting_oracle,
    meta_arbiter,
    meta_arbiter_kernel,
    meta_arbiter_types,
    metabolism,
    metacognition,
    metadata_engine,
    nemesis,
    psychology,
    right_brain,
    sovereign_arbiter,
    vision_reasoner,
)
