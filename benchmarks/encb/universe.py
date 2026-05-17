"""ENCB v2 — Proposition Universe Generator.

Generates P propositions across K semantic domains with 4 types,
ground truth assignments, and optional causal constraints.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from benchmarks.encb.belief_object import BeliefType


@dataclass
class Proposition:
    """A single proposition in the universe.

    Attributes:
        key: Unique identifier (e.g., "config.timeout_ms").
        belief_type: BOOLEAN, CATEGORICAL, SCALAR, or SET.
        ground_truth: The correct value for this proposition.
        domain: Semantic domain (e.g., "config", "model", "security").
        categories: For CATEGORICAL, the valid set of choices.
        set_universe: For SET, the full universe of possible elements.
        causal_parents: Propositions that constrain this one.
    """

    key: str
    belief_type: BeliefType
    ground_truth: Any
    domain: str
    categories: list[Any] = field(default_factory=list)
    set_universe: set = field(default_factory=set)
    causal_parents: list[str] = field(default_factory=list)


@dataclass
class Universe:
    """The full proposition universe with ground truth."""

    propositions: dict[str, Proposition]
    domains: list[str]
    causal_constraints: list[tuple[str, str, str]]  # (parent_key, rel, child_key)

    @property
    def num_propositions(self) -> int:
        return len(self.propositions)

    def ground_truth_dict(self) -> dict[str, Any]:
        """Return key → ground_truth mapping."""
        return {k: p.ground_truth for k, p in self.propositions.items()}

    def props_by_type(self, bt: BeliefType) -> list[Proposition]:
        """Filter propositions by type."""
        return [p for p in self.propositions.values() if p.belief_type == bt]

    def props_by_domain(self, domain: str) -> list[Proposition]:
        """Filter propositions by domain."""
        return [p for p in self.propositions.values() if p.domain == domain]


# ── Domain Templates ──────────────────────────────────────────────────────

_BOOLEAN_TEMPLATES = [
    ("is_default_model", True),
    ("encryption_enabled", True),
    ("auto_scale", False),
    ("debug_mode", False),
    ("strict_mode", True),
    ("cors_enabled", True),
    ("rate_limiting_on", True),
    ("logging_verbose", False),
]

_CATEGORICAL_TEMPLATES = [
    ("preferred_lang", ["python", "go", "rust", "java"], "python"),
    ("db_engine", ["sqlite", "postgres", "mysql", "alloydb"], "sqlite"),
    ("model_tier", ["small", "medium", "large", "xl"], "large"),
    ("auth_method", ["api_key", "oauth2", "jwt", "mtls"], "jwt"),
    ("region", ["us-east", "eu-west", "ap-south", "eu-central"], "eu-west"),
]

_SCALAR_TEMPLATES = [
    ("timeout_ms", 250.0),
    ("max_retries", 3.0),
    ("batch_size", 64.0),
    ("learning_rate", 0.001),
    ("cache_ttl_seconds", 3600.0),
    ("max_connections", 100.0),
    ("memory_limit_mb", 2048.0),
]

_SET_TEMPLATES = [
    ("allowed_tools", {"web", "file_search", "gcal", "code_exec"}),
    ("supported_formats", {"json", "yaml", "toml", "xml"}),
    ("active_features", {"search", "store", "graph", "audit"}),
    ("blocked_ips", {"10.0.0.1", "192.168.1.100"}),
]

_DOMAINS = [
    "config",
    "model",
    "security",
    "infra",
    "policy",
    "telemetry",
    "routing",
    "storage",
]


def generate_universe(
    n_propositions: int = 1000,
    n_domains: int = 8,
    type_distribution: dict[BeliefType, float] | None = None,
    seed: int | None = None,
) -> Universe:
    """Generate a proposition universe.

    Args:
        n_propositions: Total number of propositions.
        n_domains: Number of semantic domains (max 8).
        type_distribution: Fraction per type (must sum to 1.0).
            Defaults to 40% boolean, 25% categorical, 25% scalar, 10% set.
        seed: Random seed for reproducibility.

    Returns:
        Universe with propositions, domains, and causal constraints.
    """
    if seed is not None:
        random.seed(seed)

    if type_distribution is None:
        type_distribution = {
            BeliefType.BOOLEAN: 0.40,
            BeliefType.CATEGORICAL: 0.25,
            BeliefType.SCALAR: 0.25,
            BeliefType.SET: 0.10,
        }

    domains = _DOMAINS[:n_domains]
    props: dict[str, Proposition] = {}
    causal: list[tuple[str, str, str]] = []

    # Allocate counts per type
    counts = {}
    remaining = n_propositions
    for bt in [BeliefType.BOOLEAN, BeliefType.CATEGORICAL, BeliefType.SCALAR]:
        c = int(n_propositions * type_distribution.get(bt, 0.25))
        counts[bt] = c
        remaining -= c
    counts[BeliefType.SET] = remaining

    idx = 0

    # Boolean propositions
    for i in range(counts[BeliefType.BOOLEAN]):
        tmpl_name, tmpl_truth = _BOOLEAN_TEMPLATES[i % len(_BOOLEAN_TEMPLATES)]
        domain = domains[i % len(domains)]
        key = f"{domain}.{tmpl_name}_{idx}"
        truth = tmpl_truth if random.random() < 0.6 else (not tmpl_truth)
        props[key] = Proposition(
            key=key,
            belief_type=BeliefType.BOOLEAN,
            ground_truth=truth,
            domain=domain,
        )
        idx += 1

    # Categorical propositions
    for i in range(counts[BeliefType.CATEGORICAL]):
        tmpl_name, tmpl_cats, tmpl_default = _CATEGORICAL_TEMPLATES[i % len(_CATEGORICAL_TEMPLATES)]
        domain = domains[i % len(domains)]
        key = f"{domain}.{tmpl_name}_{idx}"
        truth = random.choice(tmpl_cats)
        props[key] = Proposition(
            key=key,
            belief_type=BeliefType.CATEGORICAL,
            ground_truth=truth,
            domain=domain,
            categories=list(tmpl_cats),
        )
        idx += 1

    # Scalar propositions
    for i in range(counts[BeliefType.SCALAR]):
        tmpl_name, tmpl_val = _SCALAR_TEMPLATES[i % len(_SCALAR_TEMPLATES)]
        domain = domains[i % len(domains)]
        key = f"{domain}.{tmpl_name}_{idx}"
        # Add some noise to ground truth to make it varied
        truth = tmpl_val * random.uniform(0.5, 2.0)
        props[key] = Proposition(
            key=key,
            belief_type=BeliefType.SCALAR,
            ground_truth=round(truth, 4),
            domain=domain,
        )
        idx += 1

    # Set propositions
    for i in range(counts[BeliefType.SET]):
        tmpl_name, tmpl_set = list(_SET_TEMPLATES)[i % len(_SET_TEMPLATES)]
        domain = domains[i % len(domains)]
        key = f"{domain}.{tmpl_name}_{idx}"
        # Random subset as ground truth
        truth = set(random.sample(list(tmpl_set), k=random.randint(1, len(tmpl_set))))
        props[key] = Proposition(
            key=key,
            belief_type=BeliefType.SET,
            ground_truth=truth,
            domain=domain,
            set_universe=set(tmpl_set),
        )
        idx += 1

    # Generate causal constraints (10% of propositions)
    all_keys = list(props.keys())
    n_causal = max(1, n_propositions // 10)
    for _ in range(n_causal):
        if len(all_keys) < 2:
            break
        parent_key, child_key = random.sample(all_keys, 2)
        parent = props[parent_key]
        child = props[child_key]
        # Only create constraints between same-type or boolean→anything
        if parent.belief_type == BeliefType.BOOLEAN:
            causal.append((parent_key, "requires_true", child_key))
            child.causal_parents.append(parent_key)

    return Universe(
        propositions=props,
        domains=domains,
        causal_constraints=causal,
    )
