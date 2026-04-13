"""Runtime primitives for the continual-learning sidecar."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from cortex.extensions.continual_learning.algorithms import (
    centroid_distance_projection,
    cosine_similarity,
    ks_2samp,
    population_stability_index,
    stable_text_hash,
)
from cortex.extensions.continual_learning.models import (
    AdapterPersistence,
    AdapterSnapshot,
    AdapterState,
    AuditSink,
    BufferPersistence,
    DriftSignal,
    ExperienceRecord,
    LearningThresholds,
)

__all__ = [
    "AdapterRegistry",
    "DriftTracker",
    "InMemoryPrototypeStore",
    "InMemorySemanticMemoryStore",
    "ListRetrainQueue",
    "NoOpAuditSink",
    "PrioritizedEpisodicBuffer",
]

logger = logging.getLogger("cortex.extensions.continual_learning")


@dataclass
class _BufferEntry:
    """Internal buffer wrapper retaining replay metadata."""

    experience: ExperienceRecord
    priority: float
    inserted_at: float
    last_seen_at: float
    novelty: float
    pinned_anchor: bool
    dedup_group_id: str


class NoOpAuditSink:
    """Default audit sink used when ledger integration is not yet wired."""

    def emit(self, event_type: str, tenant_id: str, payload: dict[str, Any]) -> None:
        """Drop events while keeping a uniform call site."""
        logger.debug(
            "continual_learning audit=%s tenant=%s payload=%s",
            event_type,
            tenant_id,
            payload,
        )


class InMemoryPrototypeStore:
    """Simple in-memory prototype store for deterministic tests and local runs."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], list[ExperienceRecord]] = defaultdict(list)

    def add(self, tenant_id: str, domain: str, examples: Sequence[ExperienceRecord]) -> None:
        """Append prototype candidates for a tenant/domain."""
        key = (tenant_id.strip(), domain.strip())
        self._items[key].extend(examples)

    def sample(self, tenant_id: str, domain: str, k: int) -> Sequence[ExperienceRecord]:
        """Return the most recent prototypes for the requested scope."""
        key = (tenant_id.strip(), domain.strip())
        return tuple(self._items.get(key, [])[: max(k, 0)])

    def purge_by_source_ids(self, source_ids: Sequence[str]) -> int:
        """Delete prototypes that originated from deleted examples."""
        source_set = set(source_ids)
        deleted = 0
        for key, items in list(self._items.items()):
            kept = [item for item in items if item.id not in source_set]
            deleted += len(items) - len(kept)
            self._items[key] = kept
        return deleted


class InMemorySemanticMemoryStore:
    """Minimal semantic store used to exercise selective forgetting flows."""

    def __init__(self) -> None:
        self._chunks: dict[str, list[dict[str, str]]] = defaultdict(list)

    def add(self, tenant_id: str, chunk_id: str, text: str) -> None:
        """Store a chunk for later delete-by-query tests."""
        self._chunks[tenant_id.strip()].append({"chunk_id": chunk_id, "text": text})

    def delete_by_query(self, tenant_id: str, query: str) -> list[str]:
        """Delete chunks whose text contains the supplied query."""
        tenant_key = tenant_id.strip()
        needle = query.lower().strip()
        deleted: list[str] = []
        kept: list[dict[str, str]] = []
        for chunk in self._chunks.get(tenant_key, []):
            if needle and needle in chunk["text"].lower():
                deleted.append(chunk["chunk_id"])
            else:
                kept.append(chunk)
        self._chunks[tenant_key] = kept
        return deleted


class ListRetrainQueue:
    """List-backed queue recorder for replay requests."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def put(self, job: dict[str, Any]) -> None:
        """Append a replay job."""
        self.items.append(dict(job))


class PrioritizedEpisodicBuffer:
    """Tenant-scoped prioritized replay buffer with TTL and semantic deduplication."""

    def __init__(
        self,
        *,
        max_items: int,
        ttl_seconds: int,
        dedup_tau: float,
        audit_sink: AuditSink | None = None,
        clock: Callable[[], float] | None = None,
        persistence: BufferPersistence | None = None,
    ) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be > 0")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        if not 0.0 <= dedup_tau <= 1.0:
            raise ValueError("dedup_tau must be between 0.0 and 1.0")

        self._max_items = max_items
        self._ttl_seconds = ttl_seconds
        self._dedup_tau = dedup_tau
        self._audit_sink = audit_sink or NoOpAuditSink()
        self._clock = clock or time.time
        self._persistence = persistence
        self._entries: dict[str, _BufferEntry] = {}
        self._hydrate()

    def __len__(self) -> int:
        """Return the number of live buffer entries."""
        self._evict_expired()
        return len(self._entries)

    def add(
        self,
        experience: ExperienceRecord,
        *,
        novelty: float = 1.0,
        pinned_anchor: bool = False,
    ) -> str:
        """Insert or merge an experience into the buffer."""
        self._evict_expired()

        duplicate_id = self._find_duplicate(experience)
        now = self._clock()
        if duplicate_id is not None:
            existing = self._entries[duplicate_id]
            existing.priority = max(existing.priority, experience.priority)
            existing.last_seen_at = now
            existing.pinned_anchor = existing.pinned_anchor or pinned_anchor
            self._persist_entry(existing)
            self._audit_sink.emit(
                "buffer.deduplicated",
                experience.tenant_id,
                {
                    "experience_id": duplicate_id,
                    "trace_id": experience.trace_id,
                    "priority": existing.priority,
                },
            )
            return duplicate_id

        dedup_group_id = experience.semantic_hash or stable_text_hash(experience.text)
        self._entries[experience.id] = _BufferEntry(
            experience=experience,
            priority=experience.priority,
            inserted_at=now,
            last_seen_at=now,
            novelty=max(novelty, 0.0),
            pinned_anchor=pinned_anchor,
            dedup_group_id=dedup_group_id,
        )
        self._persist_entry(self._entries[experience.id])
        self._audit_sink.emit(
            "buffer.inserted",
            experience.tenant_id,
            {
                "experience_id": experience.id,
                "domain": experience.domain,
                "trace_id": experience.trace_id,
                "pinned_anchor": pinned_anchor,
            },
        )
        self._evict_over_capacity()
        return experience.id

    def sample(
        self,
        *,
        tenant_id: str,
        domain: str | None,
        k: int,
        anchors_only: bool = False,
        high_priority: bool = True,
    ) -> tuple[ExperienceRecord, ...]:
        """Sample up to ``k`` examples, always preserving tenant isolation."""
        if k <= 0:
            return ()

        self._evict_expired()
        tenant_key = tenant_id.strip()
        domain_key = domain.strip() if domain is not None else None

        candidates = [
            entry
            for entry in self._entries.values()
            if entry.experience.tenant_id == tenant_key
            and (domain_key is None or entry.experience.domain == domain_key)
            and (not anchors_only or entry.pinned_anchor)
        ]
        if not candidates and anchors_only:
            candidates = [
                entry for entry in self._entries.values() if entry.experience.tenant_id == tenant_key
            ]

        if high_priority:
            candidates.sort(
                key=lambda entry: (entry.priority, entry.novelty, entry.last_seen_at),
                reverse=True,
            )
        else:
            candidates.sort(key=lambda entry: entry.last_seen_at, reverse=True)
        return tuple(entry.experience for entry in candidates[:k])

    def delete_by_query(self, *, tenant_id: str, query: str) -> list[str]:
        """Delete matching experiences from the buffer."""
        self._evict_expired()
        tenant_key = tenant_id.strip()
        needle = query.lower().strip()
        deleted_ids: list[str] = []
        for experience_id, entry in list(self._entries.items()):
            if entry.experience.tenant_id != tenant_key:
                continue
            haystacks = [entry.experience.text.lower(), entry.experience.trace_id.lower()]
            if needle and any(needle in haystack for haystack in haystacks):
                deleted_ids.append(experience_id)
                del self._entries[experience_id]
        if deleted_ids and self._persistence is not None:
            self._persistence.delete_buffer_entries(tuple(deleted_ids))

        if deleted_ids:
            self._audit_sink.emit(
                "buffer.deleted",
                tenant_key,
                {"experience_ids": deleted_ids, "query": query},
            )
        return deleted_ids

    def embeddings_for_scope(
        self, *, tenant_id: str, domain: str | None
    ) -> list[tuple[float, ...]]:
        """Return embeddings for the requested scope."""
        self._evict_expired()
        tenant_key = tenant_id.strip()
        domain_key = domain.strip() if domain is not None else None
        return [
            entry.experience.embedding
            for entry in self._entries.values()
            if entry.experience.tenant_id == tenant_key
            and (domain_key is None or entry.experience.domain == domain_key)
            and entry.experience.embedding
        ]

    def _find_duplicate(self, experience: ExperienceRecord) -> str | None:
        """Find an existing semantically equivalent experience in the same tenant."""
        if not experience.embedding:
            return None
        for existing_id, entry in self._entries.items():
            if entry.experience.tenant_id != experience.tenant_id:
                continue
            if not entry.experience.embedding:
                continue
            if (
                cosine_similarity(entry.experience.embedding, experience.embedding)
                >= self._dedup_tau
            ):
                return existing_id
        return None

    def _evict_expired(self) -> None:
        """Evict entries that exceeded TTL."""
        now = self._clock()
        for experience_id, entry in list(self._entries.items()):
            ttl_deadline = entry.experience.ttl_deadline or (entry.inserted_at + self._ttl_seconds)
            if ttl_deadline <= now:
                del self._entries[experience_id]
                if self._persistence is not None:
                    self._persistence.delete_buffer_entries((experience_id,))
                self._audit_sink.emit(
                    "buffer.expired",
                    entry.experience.tenant_id,
                    {"experience_id": experience_id},
                )

    def _evict_over_capacity(self) -> None:
        """Evict the lowest-priority non-anchor entries until capacity is respected."""
        while len(self._entries) > self._max_items:
            candidates = [entry for entry in self._entries.values() if not entry.pinned_anchor]
            if not candidates:
                break
            victim = min(candidates, key=lambda entry: (entry.priority, entry.last_seen_at))
            del self._entries[victim.experience.id]
            if self._persistence is not None:
                self._persistence.delete_buffer_entries((victim.experience.id,))
            self._audit_sink.emit(
                "buffer.evicted",
                victim.experience.tenant_id,
                {"experience_id": victim.experience.id, "reason": "capacity"},
            )

    def _persist_entry(self, entry: _BufferEntry) -> None:
        """Persist a single buffer entry when a store is configured."""
        if self._persistence is None:
            return
        self._persistence.save_buffer_entry(
            {
                "experience": asdict(entry.experience),
                "priority": entry.priority,
                "inserted_at": entry.inserted_at,
                "last_seen_at": entry.last_seen_at,
                "novelty": entry.novelty,
                "pinned_anchor": entry.pinned_anchor,
                "dedup_group_id": entry.dedup_group_id,
            }
        )

    def _hydrate(self) -> None:
        """Load persisted entries into memory."""
        if self._persistence is None:
            return
        for payload in self._persistence.load_buffer_entries():
            experience = ExperienceRecord(**payload["experience"])
            self._entries[experience.id] = _BufferEntry(
                experience=experience,
                priority=float(payload["priority"]),
                inserted_at=float(payload["inserted_at"]),
                last_seen_at=float(payload["last_seen_at"]),
                novelty=float(payload["novelty"]),
                pinned_anchor=bool(payload["pinned_anchor"]),
                dedup_group_id=str(payload["dedup_group_id"]),
            )


class DriftTracker:
    """Sustained drift detector over projected embedding windows."""

    def __init__(
        self,
        thresholds: LearningThresholds,
        *,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._thresholds = thresholds
        self._audit_sink = audit_sink or NoOpAuditSink()
        self._consecutive_breaches: dict[tuple[str, str], int] = defaultdict(int)

    def observe(
        self,
        *,
        tenant_id: str,
        domain: str,
        baseline_embeddings: Sequence[Sequence[float]],
        current_embeddings: Sequence[Sequence[float]],
    ) -> DriftSignal:
        """Evaluate sustained drift for a tenant/domain window."""
        reference_projection = centroid_distance_projection(baseline_embeddings)
        current_projection = centroid_distance_projection(current_embeddings)
        sample_size = int(min(reference_projection.size, current_projection.size))
        if sample_size == 0:
            return DriftSignal(
                psi=0.0,
                ks_statistic=0.0,
                ks_p_value=1.0,
                breached=False,
                consecutive_breaches=0,
                sample_size=0,
            )

        psi = population_stability_index(reference_projection, current_projection)
        ks_statistic, ks_p_value = ks_2samp(reference_projection, current_projection)
        breached = (
            psi > self._thresholds.drift_psi_threshold
            or ks_p_value < self._thresholds.drift_ks_p_threshold
        )
        key = (tenant_id.strip(), domain.strip())
        if breached:
            self._consecutive_breaches[key] += 1
        else:
            self._consecutive_breaches[key] = 0

        signal = DriftSignal(
            psi=psi,
            ks_statistic=ks_statistic,
            ks_p_value=ks_p_value,
            breached=breached,
            consecutive_breaches=self._consecutive_breaches[key],
            sample_size=sample_size,
        )
        self._audit_sink.emit(
            "drift.observed",
            tenant_id,
            {
                "domain": domain,
                "psi": psi,
                "ks_statistic": ks_statistic,
                "ks_p_value": ks_p_value,
                "breached": breached,
                "consecutive_breaches": signal.consecutive_breaches,
            },
        )
        return signal


class AdapterRegistry:
    """In-memory adapter registry with snapshot and rollback support."""

    def __init__(
        self,
        *,
        audit_sink: AuditSink | None = None,
        clock: Callable[[], float] | None = None,
        persistence: AdapterPersistence | None = None,
    ) -> None:
        self._audit_sink = audit_sink or NoOpAuditSink()
        self._clock = clock or time.time
        self._persistence = persistence
        self._active_by_scope: dict[tuple[str, str], str] = {}
        self._states: dict[str, AdapterState] = {}
        self._snapshots: dict[str, list[AdapterSnapshot]] = defaultdict(list)
        self._rollback_streaks: dict[tuple[str, str], int] = defaultdict(int)
        self._hydrate()

    def get_active_adapter(self, tenant_id: str, domain: str) -> str | None:
        """Return the active adapter identifier for a tenant/domain."""
        return self._active_by_scope.get((tenant_id.strip(), domain.strip()))

    def get_state(self, adapter_id: str) -> AdapterState | None:
        """Return the registry state for an adapter when present."""
        return self._states.get(adapter_id)

    def get_or_create_active_adapter(
        self,
        *,
        tenant_id: str,
        domain: str,
        base_model_id: str,
        rank_r: int,
    ) -> str:
        """Return the active adapter, creating one lazily when needed."""
        existing = self.get_active_adapter(tenant_id, domain)
        if existing is not None:
            return existing
        state = self.create_adapter(
            tenant_id=tenant_id,
            domain=domain,
            base_model_id=base_model_id,
            rank_r=rank_r,
        )
        self.set_active_adapter(tenant_id, domain, state.adapter_id)
        return state.adapter_id

    def create_adapter(
        self,
        *,
        tenant_id: str,
        domain: str,
        base_model_id: str,
        rank_r: int,
        parent_adapter_id: str | None = None,
        path_weights: str = "",
    ) -> AdapterState:
        """Create a new adapter state."""
        created_at = self._clock()
        adapter_id = f"lora:{tenant_id.strip()}:{domain.strip()}:{uuid.uuid4().hex[:12]}"
        state = AdapterState(
            adapter_id=adapter_id,
            tenant_id=tenant_id.strip(),
            domain=domain.strip(),
            base_model_id=base_model_id.strip(),
            rank_r=rank_r,
            created_at=created_at,
            parent_adapter_id=parent_adapter_id,
            path_weights=path_weights,
        )
        self._states[adapter_id] = state
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))
        self._audit_sink.emit(
            "adapter.created",
            state.tenant_id,
            {
                "adapter_id": adapter_id,
                "domain": state.domain,
                "parent_adapter_id": parent_adapter_id,
            },
        )
        return state

    def set_active_adapter(self, tenant_id: str, domain: str, adapter_id: str) -> None:
        """Activate an adapter for the supplied tenant/domain scope."""
        state = self._states[adapter_id]
        scope = (tenant_id.strip(), domain.strip())
        state.last_used_at = self._clock()
        self._active_by_scope[scope] = adapter_id
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))
            self._persistence.save_active_scope(tenant_id, domain, adapter_id)
        self._audit_sink.emit(
            "adapter.activated",
            state.tenant_id,
            {"adapter_id": adapter_id, "domain": state.domain},
        )

    def snapshot(
        self,
        *,
        adapter_id: str,
        reason: str,
        metrics: dict[str, float],
        pii_clean: bool = True,
        rollback_candidate: bool = True,
        path_weights: str = "",
        data_fingerprint: str = "",
    ) -> AdapterSnapshot:
        """Capture a rollback-capable adapter snapshot."""
        snapshot = AdapterSnapshot(
            snapshot_id=f"{adapter_id}:{int(self._clock() * 1000)}",
            adapter_id=adapter_id,
            created_at=self._clock(),
            metrics=dict(metrics),
            reason=reason,
            pii_clean=pii_clean,
            rollback_candidate=rollback_candidate,
            path_weights=path_weights,
            data_fingerprint=data_fingerprint,
        )
        self._snapshots[adapter_id].append(snapshot)
        if self._persistence is not None:
            state = self._states[adapter_id]
            payload = asdict(snapshot)
            payload["tenant_id"] = state.tenant_id
            payload["domain"] = state.domain
            self._persistence.save_adapter_snapshot(payload)
        self._audit_sink.emit(
            "adapter.snapshot",
            self._states[adapter_id].tenant_id,
            {"adapter_id": adapter_id, "snapshot_id": snapshot.snapshot_id, "reason": reason},
        )
        return snapshot

    def mark_metrics(
        self,
        adapter_id: str,
        metrics: dict[str, float],
        drift_stats: dict[str, float] | None = None,
    ) -> None:
        """Update runtime metrics tracked for an adapter."""
        state = self._states[adapter_id]
        state.metrics = dict(metrics)
        if drift_stats is not None:
            state.drift_stats = dict(drift_stats)
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))

    def update_artifact(
        self,
        adapter_id: str,
        *,
        path_weights: str = "",
        status: str | None = None,
    ) -> AdapterState:
        """Update the persisted artifact pointer and lifecycle status for an adapter."""
        state = self._states[adapter_id]
        if path_weights.strip():
            state.path_weights = path_weights.strip()
        if status is not None and status.strip():
            state.status = status.strip()
        state.last_used_at = self._clock()
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))
        return state

    def rollback(self, adapter_id: str) -> AdapterSnapshot | None:
        """Rollback to the latest eligible snapshot."""
        state = self._states[adapter_id]
        for snapshot in reversed(self._snapshots.get(adapter_id, [])):
            if snapshot.rollback_candidate:
                state.rollback_to_snapshot_id = snapshot.snapshot_id
                state.status = "rolled_back"
                state.path_weights = snapshot.path_weights
                state.metrics = dict(snapshot.metrics)
                scope = (state.tenant_id, state.domain)
                if self._persistence is not None:
                    self._rollback_streaks[scope] = self._persistence.increment_rollback_streak(
                        state.tenant_id,
                        state.domain,
                    )
                    self._persistence.save_adapter_state(asdict(state))
                else:
                    self._rollback_streaks[scope] += 1
                self._audit_sink.emit(
                    "adapter.rollback",
                    state.tenant_id,
                    {"adapter_id": adapter_id, "snapshot_id": snapshot.snapshot_id},
                )
                return snapshot
        return None

    def rollback_streak(self, tenant_id: str, domain: str) -> int:
        """Return how many consecutive rollbacks happened for a scope."""
        return self._rollback_streaks[(tenant_id.strip(), domain.strip())]

    def reset_rollback_streak(self, tenant_id: str, domain: str) -> None:
        """Clear rollback streak tracking after a successful update."""
        scope = (tenant_id.strip(), domain.strip())
        self._rollback_streaks[scope] = 0
        if self._persistence is not None:
            self._persistence.reset_rollback_streak(scope[0], scope[1])

    def _hydrate(self) -> None:
        """Load persisted registry state."""
        if self._persistence is None:
            return
        for payload in self._persistence.load_adapter_states():
            state = AdapterState(**payload)
            self._states[state.adapter_id] = state
        for payload in self._persistence.load_adapter_snapshots():
            snapshot = AdapterSnapshot(
                snapshot_id=payload["snapshot_id"],
                adapter_id=payload["adapter_id"],
                created_at=float(payload["created_at"]),
                metrics=dict(payload.get("metrics", {})),
                reason=payload.get("reason", ""),
                pii_clean=bool(payload.get("pii_clean", True)),
                rollback_candidate=bool(payload.get("rollback_candidate", True)),
                path_weights=payload.get("path_weights", ""),
                data_fingerprint=payload.get("data_fingerprint", ""),
            )
            self._snapshots[snapshot.adapter_id].append(snapshot)
        self._active_by_scope.update(self._persistence.load_active_scopes())
        self._rollback_streaks.update(self._persistence.load_rollback_streaks())
