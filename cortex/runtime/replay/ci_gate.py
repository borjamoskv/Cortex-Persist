# [C5-REAL] Exergy-Maximized
"""
Replay CI Gate — Execution Identity Verifier

No verifica "que funcione".
Verifica que el sistema NO PUEDE divergir entre ejecuciones idénticas.

Propiedad demostrada:
    Replay(run_n(events)) == Replay(run_m(events))  ∀ n,m

Esto convierte el determinismo de propiedad implícita a invariante CI demostrable.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any

from cortex.runtime.replay.engine import ReplayEngine


@dataclass(frozen=True)
class ReplayCIResult:
    """Resultado inmutable de una verificación CI de replay."""

    passed: bool
    runs_executed: int
    events_per_run: int
    hash_chain: tuple[str, ...]
    divergence_point: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "runs_executed": self.runs_executed,
            "events_per_run": self.events_per_run,
            "hash_chain_digest": hashlib.sha256(
                json.dumps(self.hash_chain, sort_keys=True).encode()
            ).hexdigest()[:16],
            "divergence_point": self.divergence_point,
            "error": self.error,
        }


def fixed_event_trace(seed: int = 42, length: int = 20) -> list[dict[str, Any]]:
    """
    Genera una traza de eventos determinista a partir de una semilla.
    Siempre produce la misma secuencia para la misma semilla.
    """
    rng = random.Random(seed)
    events = []
    for tick in range(1, length + 1):
        events.append(
            {
                "action_type": "MEMORY_WRITE",
                "payload": {
                    "tick": tick,
                    f"key_{tick}": rng.randint(0, 10000),
                    "entropy": rng.random() * 100,
                },
            }
        )
    return events


class ReplayCIGate:
    """
    CI Gate that demonstrates execution identity across temporal reconstruction.

    Executes N independent replicas of the same event trace
    and verifies that ALL produce identical hash chains.

    If any diverges -> the system has lost determinism -> catastrophic failure.
    """

    def __init__(self, state_cls: type[Any], *, replicas: int = 3):
        if replicas < 2:
            raise ValueError("CI Gate requires minimum 2 replicas to verify identity.")
        self.state_cls = state_cls
        self.replicas = replicas

    def verify(
        self,
        events: list[dict[str, Any]] | None = None,
        seed: int = 42,
        trace_length: int = 20,
    ) -> ReplayCIResult:
        """
        Ejecuta la verificación completa.

        Args:
            events: Traza explícita. Si None, se genera con fixed_event_trace(seed).
            seed: Semilla para generación determinista (ignorada si events se provee).
            trace_length: Longitud de la traza generada.

        Returns:
            ReplayCIResult con el veredicto.
        """
        if events is None:
            events = fixed_event_trace(seed=seed, length=trace_length)

        reference_chain: tuple[str, ...] | None = None

        for run_idx in range(self.replicas):
            engine = ReplayEngine(self.state_cls)
            try:
                snapshots = engine.run(events)
            except (ValueError, TypeError, OSError, KeyError) as e:
                return ReplayCIResult(
                    passed=False,
                    runs_executed=run_idx + 1,
                    events_per_run=len(events),
                    hash_chain=(),
                    divergence_point=None,
                    error=f"[RUN {run_idx}] Engine crash: {e}",
                )

            current_chain = tuple(snap["state_hash"] for snap in snapshots)

            if reference_chain is None:
                reference_chain = current_chain
                continue

            # Hash-by-hash chain verification
            for version_idx, (ref_hash, cur_hash) in enumerate(
                zip(reference_chain, current_chain, strict=False)
            ):
                if ref_hash != cur_hash:
                    return ReplayCIResult(
                        passed=False,
                        runs_executed=run_idx + 1,
                        events_per_run=len(events),
                        hash_chain=reference_chain,
                        divergence_point=version_idx,
                        error=(
                            f"[DIVERGENCE] Run 0 vs Run {run_idx} at version {version_idx}: "
                            f"{ref_hash[:16]}… ≠ {cur_hash[:16]}…"
                        ),
                    )

            # Length mismatch check
            if len(current_chain) != len(reference_chain):
                return ReplayCIResult(
                    passed=False,
                    runs_executed=run_idx + 1,
                    events_per_run=len(events),
                    hash_chain=reference_chain,
                    divergence_point=min(len(reference_chain), len(current_chain)),
                    error=(
                        f"[DIVERGENCE] Chain length mismatch: "
                        f"Run 0 has {len(reference_chain)}, Run {run_idx} has {len(current_chain)}"
                    ),
                )

        assert reference_chain is not None
        return ReplayCIResult(
            passed=True,
            runs_executed=self.replicas,
            events_per_run=len(events),
            hash_chain=reference_chain,
        )
