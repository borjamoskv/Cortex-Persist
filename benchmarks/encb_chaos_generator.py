"""
ENCB — Epistemic Noise Chaos Benchmark: Chaos Generator
=========================================================
Generates structured epistemic noise in three modalities to stress-test
CORTEX's cognitive governance layer.

Modalities:
  1. Temporal Contradiction: P(H)=0.9 → P(H)=0.1 flip sequences
  2. Transitive Breakage: Invalidation of root nodes in entails chains
  3. Episodic Spam: Mass injection of semantically similar but epistemically null facts

Nobel-Ω Vector Ξ₄ — Empirical Falsification Experiment.
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any


class ChaosModality(str, Enum):
    """The three epistemic noise dimensions."""

    TEMPORAL_CONTRADICTION = "temporal_contradiction"
    TRANSITIVE_BREAKAGE = "transitive_breakage"
    EPISODIC_SPAM = "episodic_spam"


@dataclass(frozen=True)
class ChaosEvent:
    """A single unit of injected epistemic noise."""

    modality: ChaosModality
    agent_id: str
    content: str
    fact_type: str
    confidence: str
    tags: tuple[str, ...]
    meta: MappingProxyType[str, Any]
    timestamp: float = field(default_factory=time.time)

    @property
    def event_id(self) -> str:
        raw = f"{self.agent_id}:{self.content}:{self.timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class GroundTruth:
    """The known correct state that the system must recover."""

    propositions: dict[str, bool]  # proposition_text → True/False
    entails_chains: list[list[str]]  # ordered dependency chains
    signal_facts: list[str]  # real facts (non-spam)

    @property
    def total_propositions(self) -> int:
        return len(self.propositions)


# ── Modality 1: Temporal Contradiction Generator ───────────────────────────


class TemporalContradictionGenerator:
    """Generates sequences where a proposition flips between high and low confidence.

    Parameters:
        lambda_flip: number of flips per simulated hour.
        num_propositions: how many independent propositions to generate.
        num_agents: number of simulated agents (some honest, some liars).
        byzantine_ratio: fraction of agents that will lie (0.0 to 0.5).
    """

    def __init__(
        self,
        lambda_flip: float = 5.0,
        num_propositions: int = 10,
        num_agents: int = 7,
        byzantine_ratio: float = 0.3,
    ) -> None:
        self.lambda_flip = lambda_flip
        self.num_propositions = num_propositions
        self.num_agents = num_agents
        self.byzantine_ratio = byzantine_ratio

        self._propositions: list[str] = []
        self._ground_truth: dict[str, bool] = {}
        self._agents: list[str] = []
        self._byzantine_agents: set[str] = set()

    def setup(self) -> GroundTruth:
        """Initialize propositions, agents, and ground truth."""
        self._propositions = [
            f"Proposition_{i}: {self._random_scientific_claim(i)}"
            for i in range(self.num_propositions)
        ]
        # Ground truth: even-indexed propositions are True, odd are False
        self._ground_truth = {p: (i % 2 == 0) for i, p in enumerate(self._propositions)}

        self._agents = [f"agent_{i:03d}" for i in range(self.num_agents)]
        num_byzantine = max(1, int(self.num_agents * self.byzantine_ratio))
        self._byzantine_agents = set(random.sample(self._agents, num_byzantine))

        return GroundTruth(
            propositions=dict(self._ground_truth),
            entails_chains=[],
            signal_facts=list(self._ground_truth.keys()),
        )

    def generate(self, num_rounds: int = 20) -> list[ChaosEvent]:
        """Generate temporal contradiction events across multiple rounds."""
        events: list[ChaosEvent] = []
        base_time = time.time()

        for round_idx in range(num_rounds):
            t = base_time + round_idx * (3600 / self.lambda_flip)

            for prop in self._propositions:
                truth = self._ground_truth[prop]

                for agent in self._agents:
                    is_byzantine = agent in self._byzantine_agents
                    # Byzantine agents flip the truth with high probability
                    if is_byzantine:
                        reported_truth = not truth if random.random() < 0.8 else truth
                        conf = "C5" if random.random() < 0.6 else "C4"
                    else:
                        # Honest agents report truth, occasionally uncertain
                        reported_truth = truth if random.random() < 0.95 else not truth
                        conf = "C4" if random.random() < 0.7 else "C3"

                    content = (
                        f"{prop} is {'TRUE' if reported_truth else 'FALSE'} " f"(round {round_idx})"
                    )

                    events.append(
                        ChaosEvent(
                            modality=ChaosModality.TEMPORAL_CONTRADICTION,
                            agent_id=agent,
                            content=content,
                            fact_type="decision",
                            confidence=conf,
                            tags=tuple(["encb", "temporal-contradiction", f"round-{round_idx}"]),
                            meta=MappingProxyType(
                                {
                                    "proposition": prop,
                                    "reported_value": reported_truth,
                                    "ground_truth": truth,
                                    "is_byzantine": is_byzantine,
                                    "round": round_idx,
                                }
                            ),
                            timestamp=t,
                        )
                    )

        return events

    @staticmethod
    def _random_scientific_claim(idx: int) -> str:
        claims = [
            "Quantum entanglement enables FTL communication",
            "CRISPR-Cas9 can safely edit human germline cells",
            "Dark matter consists of WIMPs",
            "P equals NP",
            "Consciousness emerges from quantum coherence in microtubules",
            "mRNA vaccines can be reprogrammed for cancer in vivo",
            "Graphene superconducts at room temperature",
            "Shannon entropy is bounded for finite alphabets",
            "Byzantine consensus requires 3f+1 nodes",
            "CRDTs guarantee strong eventual consistency",
            "LogOP preserves external Bayesianity",
            "Sparse Merkle Trees provide O(log n) verification",
            "Zero-knowledge proofs enable private auditing",
            "Iceoryx2 achieves zero-copy IPC",
            "Zenoh outperforms MQTT for edge swarms",
        ]
        return claims[idx % len(claims)]


# ── Modality 2: Transitive Breakage Generator ─────────────────────────────


class TransitiveBreakageGenerator:
    """Generates entails chains of depth d, then invalidates random roots.

    Parameters:
        chain_depth: depth of each entails chain (5-10).
        num_chains: number of independent chains to generate.
        p_break: probability of breaking each root node.
    """

    def __init__(
        self,
        chain_depth: int = 7,
        num_chains: int = 5,
        p_break: float = 0.4,
    ) -> None:
        self.chain_depth = chain_depth
        self.num_chains = num_chains
        self.p_break = p_break

        self._chains: list[list[str]] = []

    def setup(self) -> GroundTruth:
        """Build entails chains."""
        self._chains = []
        all_propositions: dict[str, bool] = {}

        for chain_idx in range(self.num_chains):
            chain: list[str] = []
            for depth in range(self.chain_depth):
                prop = f"Chain_{chain_idx}_Depth_{depth}: Lemma_{chain_idx}_{depth}"
                chain.append(prop)
                all_propositions[prop] = True  # All start as valid
            self._chains.append(chain)

        return GroundTruth(
            propositions=all_propositions,
            entails_chains=[list(c) for c in self._chains],
            signal_facts=list(all_propositions.keys()),
        )

    def generate(self) -> list[ChaosEvent]:
        """Generate events: first build chains, then break roots."""
        events: list[ChaosEvent] = []
        base_time = time.time()

        # Phase 1: Establish the chains (all valid)
        for chain_idx, chain in enumerate(self._chains):
            for depth, prop in enumerate(chain):
                parent = chain[depth - 1] if depth > 0 else None
                events.append(
                    ChaosEvent(
                        modality=ChaosModality.TRANSITIVE_BREAKAGE,
                        agent_id="chain_builder",
                        content=f"ESTABLISH: {prop}",
                        fact_type="decision",
                        confidence="C5",
                        tags=tuple(["encb", "transitive", "establish", f"chain-{chain_idx}"]),
                        meta=MappingProxyType(
                            {
                                "proposition": prop,
                                "chain_idx": chain_idx,
                                "depth": depth,
                                "parent": parent,
                                "phase": "establish",
                            }
                        ),
                        timestamp=base_time + chain_idx * 10 + depth,
                    )
                )

        # Phase 2: Break random roots
        broken_roots: list[str] = []
        for chain_idx, chain in enumerate(self._chains):
            if random.random() < self.p_break:
                root = chain[0]
                broken_roots.append(root)
                events.append(
                    ChaosEvent(
                        modality=ChaosModality.TRANSITIVE_BREAKAGE,
                        agent_id="root_breaker",
                        content=f"INVALIDATE: {root} — evidence disproven",
                        fact_type="error",
                        confidence="C5",
                        tags=tuple(["encb", "transitive", "break", f"chain-{chain_idx}"]),
                        meta=MappingProxyType(
                            {
                                "proposition": root,
                                "chain_idx": chain_idx,
                                "phase": "break",
                                "cascade_depth": len(chain),
                            }
                        ),
                        timestamp=base_time + 1000 + chain_idx,
                    )
                )

        return events

    @property
    def chains(self) -> list[list[str]]:
        return [list(c) for c in self._chains]


# ── Modality 3: Episodic Spam Generator ────────────────────────────────────


class EpisodicSpamGenerator:
    """Injects semantically similar but epistemically null facts.

    Parameters:
        rho_noise: noise-to-signal ratio (e.g., 10 = 10 spam per 1 signal).
        num_signal_facts: number of real (signal) facts.
        semantic_similarity: how close spam is to signal (0.0-1.0).
    """

    def __init__(
        self,
        rho_noise: float = 10.0,
        num_signal_facts: int = 10,
        semantic_similarity: float = 0.85,
    ) -> None:
        self.rho_noise = rho_noise
        self.num_signal_facts = num_signal_facts
        self.semantic_similarity = semantic_similarity

        self._signal_facts: list[str] = []

    def setup(self) -> GroundTruth:
        """Create signal facts."""
        self._signal_facts = [self._generate_signal_fact(i) for i in range(self.num_signal_facts)]
        return GroundTruth(
            propositions={f: True for f in self._signal_facts},
            entails_chains=[],
            signal_facts=list(self._signal_facts),
        )

    def generate(self) -> list[ChaosEvent]:
        """Generate signal + spam events."""
        events: list[ChaosEvent] = []
        base_time = time.time()

        # Phase 1: Inject signal facts
        for i, fact in enumerate(self._signal_facts):
            events.append(
                ChaosEvent(
                    modality=ChaosModality.EPISODIC_SPAM,
                    agent_id="signal_source",
                    content=fact,
                    fact_type="discovery",
                    confidence="C5",
                    tags=tuple(["encb", "spam-test", "signal"]),
                    meta=MappingProxyType({"is_signal": True, "signal_idx": i}),
                    timestamp=base_time + i,
                )
            )

        # Phase 2: Inject spam (semantically similar noise)
        num_spam = int(self.num_signal_facts * self.rho_noise)
        for i in range(num_spam):
            # Pick a random signal fact and paraphrase it
            source_fact = random.choice(self._signal_facts)
            spam_content = self._paraphrase_as_spam(source_fact, i)
            events.append(
                ChaosEvent(
                    modality=ChaosModality.EPISODIC_SPAM,
                    agent_id=f"spam_bot_{i % 5:02d}",
                    content=spam_content,
                    fact_type="decision",
                    confidence=random.choice(["C3", "C4", "C5"]),
                    tags=tuple(["encb", "spam-test", "noise"]),
                    meta=MappingProxyType(
                        {
                            "is_signal": False,
                            "source_signal": source_fact,
                            "spam_idx": i,
                            "similarity_target": self.semantic_similarity,
                        }
                    ),
                    timestamp=base_time + 100 + i * 0.1,
                )
            )

        return events

    @staticmethod
    def _generate_signal_fact(idx: int) -> str:
        facts = [
            "CORTEX uses SHA-256 hash chains for ledger integrity",
            "Byzantine consensus requires 2/3 + 1 honest nodes",
            "CRDTs converge without coordination in eventually consistent systems",
            "Logarithmic Opinion Pool preserves external Bayesianity under independence",
            "Sparse Merkle Trees allow O(log n) non-membership proofs",
            "Zero-copy IPC via shared memory eliminates serialization overhead",
            "Zenoh peer-to-peer routing reduces median latency by 40% vs MQTT",
            "Belief Objects encode epistemic state as (confidence, uncertainty, status)",
            "The Cognitive Hypervisor arbitrates working memory retention",
            "Semantic embeddings enable sub-linear similarity search via ANN",
            "Forgetting is a feature: controlled decay reduces entropy accumulation",
            "Reputation slashing penalizes Byzantine agents by 20% per false proposal",
        ]
        return facts[idx % len(facts)]

    def _paraphrase_as_spam(self, source: str, idx: int) -> str:
        """Generate a semantically similar but epistemically null paraphrase."""
        noise_tokens = [
            "interestingly",
            "notably",
            "essentially",
            "fundamentally",
            "basically",
            "arguably",
            "reportedly",
            "supposedly",
            "in theory",
            "conceptually",
            "it seems that",
            "one could say",
        ]
        # Shuffle words, add filler, change order
        words = source.split()
        filler = random.choice(noise_tokens)

        if idx % 3 == 0:
            return f"{filler}, {source.lower()} (ref: unverified)"
        elif idx % 3 == 1:
            random.shuffle(words)
            return f"{' '.join(words)} — {filler}"
        else:
            return f"Re: {source[:40]}... {filler}, this is well-known"


# ── Unified Chaos Orchestrator ─────────────────────────────────────────────


class EpistemicChaosOrchestrator:
    """Orchestrates all three chaos modalities and tracks ground truth."""

    def __init__(
        self,
        *,
        lambda_flip: float = 5.0,
        num_propositions: int = 10,
        num_agents: int = 7,
        byzantine_ratio: float = 0.3,
        chain_depth: int = 7,
        num_chains: int = 5,
        p_break: float = 0.4,
        rho_noise: float = 10.0,
        num_signal_facts: int = 10,
        seed: int | None = None,
    ) -> None:
        if seed is not None:
            random.seed(seed)

        self.temporal = TemporalContradictionGenerator(
            lambda_flip=lambda_flip,
            num_propositions=num_propositions,
            num_agents=num_agents,
            byzantine_ratio=byzantine_ratio,
        )
        self.transitive = TransitiveBreakageGenerator(
            chain_depth=chain_depth,
            num_chains=num_chains,
            p_break=p_break,
        )
        self.spam = EpisodicSpamGenerator(
            rho_noise=rho_noise,
            num_signal_facts=num_signal_facts,
        )

        self._ground_truths: dict[ChaosModality, GroundTruth] = {}

    def setup_all(self) -> dict[ChaosModality, GroundTruth]:
        """Initialize all generators and return ground truths."""
        self._ground_truths = {
            ChaosModality.TEMPORAL_CONTRADICTION: self.temporal.setup(),
            ChaosModality.TRANSITIVE_BREAKAGE: self.transitive.setup(),
            ChaosModality.EPISODIC_SPAM: self.spam.setup(),
        }
        return dict(self._ground_truths)

    def generate_all(
        self,
        *,
        temporal_rounds: int = 20,
    ) -> dict[ChaosModality, list[ChaosEvent]]:
        """Generate chaos events for all modalities."""
        return {
            ChaosModality.TEMPORAL_CONTRADICTION: self.temporal.generate(
                num_rounds=temporal_rounds,
            ),
            ChaosModality.TRANSITIVE_BREAKAGE: self.transitive.generate(),
            ChaosModality.EPISODIC_SPAM: self.spam.generate(),
        }

    @property
    def ground_truths(self) -> dict[ChaosModality, GroundTruth]:
        return dict(self._ground_truths)

    def total_events(self, events: dict[ChaosModality, list[ChaosEvent]]) -> int:
        return sum(len(v) for v in events.values())
