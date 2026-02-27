# cortex/evolution/cortex_metrics.py
"""Real Telemetry from CORTEX DB — Afferent Signals for Fitness Computation.

Replaces stochastic (random.uniform) fitness signals with empirical
measurements from the CORTEX fact store.  Each AgentDomain maps to a
project axis in the DB; metrics are fetched asynchronously via aiosqlite.

Terminology (Computational Neuroscience & Evolutionary Biology):

    **Afferent signal** — Raw metric from DB → strategy input.
        Analogous to sensory afferents in the dorsal column-medial
        lemniscus pathway (Mountcastle, 1957).

    **Efferent modulation** — Strategy output → fitness delta.
        The motor output of the evolutionary controller.

    **Tonic baseline** — Default metrics when DB is unavailable.
        Homeostatic set-point (Turrigiano & Nelson, 2004).

    **Phasic burst** — Large metric change → amplified fitness delta.
        Models the phasic dopaminergic reward prediction error
        (Schultz, Dayan & Montague, 1997).

    **Hebbian reinforcement** — Success facts → increased fitness.
        Mirrors long-term potentiation (LTP) at corticostriatal
        synapses (Bliss & Lømo, 1973).

    **Anti-Hebbian penalty** — Error/ghost accumulation → decreased fitness.
        Analogous to long-term depression (LTD) via mGluR-dependent
        endocannabinoid signalling (Lovinger, 2010).

    **Decision success rate** — Ratio of decisions to errors.
        Proxy for the LTP/LTD balance in synaptic plasticity.

References:
    Bliss, T.V.P. & Lømo, T. (1973). J. Physiol. 232(2), 331–356.
    Hebb, D.O. (1949). The Organization of Behavior. Wiley.
    Holland, J.H. (1975). Adaptation in Natural and Artificial Systems.
    Kauffman, S.A. (1993). The Origins of Order.
    Schultz, W. et al. (1997). Science 275(5306), 1593–1599.
    Sherrington, C.S. (1906). The Integrative Action of the Nervous System.
    Turrigiano, G.G. & Nelson, S.B. (2004). Nat. Rev. Neurosci. 5(2), 97–107.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.evolution.agents import AgentDomain

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("~/.cortex/cortex.db").expanduser()

# ── Afferent Routing Table ─────────────────────────────────────
# Maps each AgentDomain to its primary CORTEX project(s).
# Multi-project domains aggregate metrics across all listed projects.
DOMAIN_PROJECT_MAP: dict[AgentDomain, list[str]] = {
    AgentDomain.FABRICATION: ["cortex", "naroa-2026"],
    AgentDomain.ORCHESTRATION: ["cortex"],
    AgentDomain.SWARM: ["cortex"],
    AgentDomain.EVOLUTION: ["cortex"],
    AgentDomain.SECURITY: ["cortex"],
    AgentDomain.PERCEPTION: ["cortex", "notch-live"],
    AgentDomain.MEMORY: ["cortex"],
    AgentDomain.EXPERIENCE: ["naroa-2026", "notch-live"],
    AgentDomain.COMMUNICATION: ["cortex"],
    AgentDomain.VERIFICATION: ["cortex"],
}


@dataclass
class DomainMetrics:
    """Afferent telemetry vector for a single AgentDomain.

    Each field is a **sensory channel** feeding the strategy pipeline —
    analogous to proprioceptive input in the spinal reflex arc
    (Sherrington, 1906).

    The ``fitness_delta`` property computes a bounded efferent signal
    from the afferent inputs, implementing a simplified model of
    reward-prediction error (Schultz et al., 1997).

    Attributes:
        domain:  The agent domain this snapshot describes.
        error_count:  Unresolved error facts (anti-Hebbian signal).
        ghost_count:  Open ghosts — technical debt markers.
        bridge_count:  Cross-project pattern transfers (Hebbian bridges).
        decision_count:  Explicit decisions stored (crystallised knowledge).
        knowledge_count:  Pure knowledge facts (background context).
        last_decision_age_hours:  Hours since most recent decision (recency).
        fact_density:  Total facts across the domain's projects.
    """

    domain: AgentDomain = AgentDomain.FABRICATION
    error_count: int = 0
    ghost_count: int = 0
    bridge_count: int = 0
    decision_count: int = 0
    knowledge_count: int = 0
    last_decision_age_hours: float = float("inf")
    fact_density: int = 0
    _fetched_at: float = field(default_factory=time.time)

    # ── Derived Signals ────────────────────────────────────────

    @property
    def health_score(self) -> float:
        """Homeostatic health index ∈ [0, 1].

        Models the tonic firing rate of a domain's "health neuron":
        high errors/ghosts depress it (LTD), bridges/decisions potentiate
        it (LTP).
        """
        penalty = min(1.0, self.error_count * 0.10 + self.ghost_count * 0.05)
        reward = min(1.0, self.bridge_count * 0.15 + self.decision_count * 0.05)
        return max(0.0, min(1.0, 0.5 + reward - penalty))

    @property
    def decision_success_rate(self) -> float:
        """LTP/LTD ratio proxy — decisions vs errors.

        Higher values indicate more crystallised successful knowledge
        relative to failure signals.  Analogous to the long-term
        potentiation / long-term depression balance at corticostriatal
        synapses (Bliss & Lømo, 1973; Lovinger, 2010).
        """
        total = self.decision_count + self.error_count
        if total == 0:
            return 0.5  # Uninformative prior
        return self.decision_count / total

    @property
    def fitness_delta(self) -> float:
        """Efferent fitness signal ∈ [-5.0, +5.0].

        Implements a simplified reward-prediction error:
            δ = Σ(Hebbian signals) − Σ(anti-Hebbian signals) + recency_bonus

        Positive → domain thriving (Hebbian LTP).
        Negative → domain struggling (anti-Hebbian LTD).
        """
        raw = (
            self.bridge_count * 2.0  # Hebbian: cross-project transfer
            + self.decision_count * 0.5  # Crystallised knowledge
            - self.error_count * 1.5  # Anti-Hebbian: failure signal
            - self.ghost_count * 1.0  # Debt accumulation
        )
        # Phasic recency bonus (dopaminergic salience)
        if self.last_decision_age_hours < 24:
            raw += 1.5
        elif self.last_decision_age_hours > 168:  # >1 week stale
            raw -= 1.0
        return max(-5.0, min(5.0, raw))

    @property
    def is_stale(self) -> bool:
        """True if snapshot older than 120 s (cache TTL)."""
        return (time.time() - self._fetched_at) > 120.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.name,
            "error_count": self.error_count,
            "ghost_count": self.ghost_count,
            "bridge_count": self.bridge_count,
            "decision_count": self.decision_count,
            "health": round(self.health_score, 2),
            "fitness_delta": round(self.fitness_delta, 2),
            "decision_success_rate": round(self.decision_success_rate, 4),
        }


# ── Tonic Baseline (homeostatic set-point) ─────────────────────
_TONIC = DomainMetrics()


# ── Async DB Queries ───────────────────────────────────────────


async def fetch_domain_metrics(
    domain: AgentDomain,
    db_path: str | Path = _DEFAULT_DB,
) -> DomainMetrics:
    """Query CORTEX DB for real afferent telemetry.

    Falls back to tonic baseline if the DB is missing or queries fail —
    graceful degradation analogous to homeostatic plasticity
    (Turrigiano & Nelson, 2004).

    Args:
        domain: The AgentDomain to query metrics for.
        db_path: Path to the CORTEX SQLite database.

    Returns:
        DomainMetrics with live values or tonic defaults.
    """
    db = Path(db_path)
    if not db.exists():
        return DomainMetrics(domain=domain)

    projects = DOMAIN_PROJECT_MAP.get(domain, ["cortex"])
    m = DomainMetrics(domain=domain)

    try:
        async with aiosqlite.connect(str(db_path)) as conn:
            for project in projects:
                # ── Fact counts by type ──
                for fact_type, attr in (
                    ("error", "error_count"),
                    ("bridge", "bridge_count"),
                    ("decision", "decision_count"),
                    ("knowledge", "knowledge_count"),
                ):
                    async with conn.execute(
                        "SELECT COUNT(*) FROM facts WHERE fact_type = ? AND project = ?",
                        (fact_type, project),
                    ) as cur:
                        row = await cur.fetchone()
                        if row:
                            setattr(m, attr, getattr(m, attr) + row[0])

                # ── Total facts (density) ──
                async with conn.execute(
                    "SELECT COUNT(*) FROM facts WHERE project = ?",
                    (project,),
                ) as cur:
                    row = await cur.fetchone()
                    if row:
                        m.fact_density += row[0]

            # ── Open ghosts ──
            placeholders = ",".join("?" for _ in projects)
            async with conn.execute(
                f"SELECT COUNT(*) FROM ghosts "
                f"WHERE status = 'open' AND project IN ({placeholders})",
                projects,
            ) as cur:
                row = await cur.fetchone()
                m.ghost_count = row[0] if row else 0

            # ── Last decision recency (phasic salience) ──
            async with conn.execute(
                f"SELECT MAX(created_at) FROM facts "
                f"WHERE fact_type = 'decision' AND project IN ({placeholders})",
                projects,
            ) as cur:
                row = await cur.fetchone()
                if row and row[0]:
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
                        age_s = time.time() - dt.timestamp()
                        m.last_decision_age_hours = age_s / 3600
                    except (ValueError, TypeError):
                        pass

            m._fetched_at = time.time()
            return m

    except (aiosqlite.Error, OSError) as exc:
        logger.warning(
            "cortex_metrics: afferent query failed for %s: %s",
            domain.name,
            exc,
        )
        return DomainMetrics(domain=domain)


async def fetch_all_domain_metrics(
    db_path: str | Path = _DEFAULT_DB,
) -> dict[AgentDomain, DomainMetrics]:
    """Fetch afferent telemetry for all 10 domains in parallel.

    Returns a dict keyed by AgentDomain.  Implements a full
    proprioceptive snapshot across all sensory modalities —
    Sherrington's "integrative action of the nervous system" (1906).
    """
    import asyncio

    results = await asyncio.gather(
        *(fetch_domain_metrics(d, db_path) for d in AgentDomain),
        return_exceptions=True,
    )
    metrics: dict[AgentDomain, DomainMetrics] = {}
    for domain, result in zip(AgentDomain, results, strict=True):
        if isinstance(result, DomainMetrics):
            metrics[domain] = result
        else:
            logger.warning(
                "Afferent fetch failed for %s: %s",
                domain.name,
                result,
            )
            metrics[domain] = DomainMetrics(domain=domain)
    return metrics


# ── Sync API (for EvolutionEngine in asyncio.to_thread) ───────


class CortexMetrics:
    """Sync CORTEX DB querier with per-domain caching.

    Thread-safe. Uses raw sqlite3 to avoid async conflicts
    when called from asyncio.to_thread offloads.
    """

    _CACHE_TTL: float = 60.0

    def __init__(self, db_path: str | Path = _DEFAULT_DB) -> None:
        self._db_path = Path(db_path)
        self._cache: dict[AgentDomain, DomainMetrics] = {}
        self._cache_time: float = 0.0

    def _is_cache_valid(self) -> bool:
        return bool(self._cache) and (time.time() - self._cache_time) < self._CACHE_TTL

    def get_all_metrics(self) -> dict[AgentDomain, DomainMetrics]:
        """Get metrics for all 10 domains (cached)."""
        if self._is_cache_valid():
            return dict(self._cache)
        self._refresh()
        return dict(self._cache)

    def get_domain(self, domain: AgentDomain) -> DomainMetrics:
        """Get cached metrics for a single domain."""
        if self._is_cache_valid() and domain in self._cache:
            return self._cache[domain]
        self._refresh()
        return self._cache.get(domain, DomainMetrics(domain=domain))

    # Alias for strategies.py compatibility
    get_domain_metrics = get_domain

    def _refresh(self) -> None:
        """Re-query via sync sqlite3."""
        result: dict[AgentDomain, DomainMetrics] = {}

        if not self._db_path.exists():
            for domain in AgentDomain:
                result[domain] = self._fallback(domain)
            self._cache = result
            self._cache_time = time.time()
            return

        try:
            import sqlite3

            conn = sqlite3.connect(
                str(self._db_path),
                timeout=2.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            try:
                for domain in AgentDomain:
                    result[domain] = self._query_sync(conn, domain)
            finally:
                conn.close()
        except Exception as e:
            logger.debug("Sync metrics refresh failed: %s", e)
            for domain in AgentDomain:
                if domain not in result:
                    result[domain] = self._fallback(domain)

        self._cache = result
        self._cache_time = time.time()

    def _query_sync(
        self,
        conn: Any,
        domain: AgentDomain,
    ) -> DomainMetrics:
        """Query single domain via open sqlite3 connection."""
        import sqlite3 as _sql

        projects = DOMAIN_PROJECT_MAP.get(domain, ["cortex"])
        m = DomainMetrics(domain=domain)
        ph = ",".join("?" for _ in projects)

        for fact_type, attr in (
            ("error", "error_count"),
            ("bridge", "bridge_count"),
            ("decision", "decision_count"),
            ("knowledge", "knowledge_count"),
        ):
            try:
                row = conn.execute(
                    f"SELECT COUNT(*) AS c FROM facts WHERE fact_type = ? AND project IN ({ph})",
                    (fact_type, *projects),
                ).fetchone()
                if row:
                    setattr(m, attr, row["c"] if isinstance(row, _sql.Row) else row[0])
            except _sql.OperationalError:
                pass

        # Ghosts
        try:
            row = conn.execute(
                f"SELECT COUNT(*) AS c FROM ghosts WHERE status = 'open' AND project IN ({ph})",
                projects,
            ).fetchone()
            if row:
                m.ghost_count = row["c"] if isinstance(row, _sql.Row) else row[0]
        except _sql.OperationalError:
            pass

        return m

    @staticmethod
    def _fallback(domain: AgentDomain) -> DomainMetrics:
        """Parse snapshot for rough counts."""
        m = DomainMetrics(domain=domain)
        snap = Path("~/.cortex/context-snapshot.md").expanduser()
        if not snap.exists():
            return m
        try:
            text = snap.read_text(encoding="utf-8", errors="ignore").lower()
            key = domain.name.lower()
            for line in text.splitlines():
                if key not in line:
                    continue
                if "error" in line:
                    m.error_count += 1
                if "ghost" in line:
                    m.ghost_count += 1
                if "bridge" in line:
                    m.bridge_count += 1
                if "decision" in line:
                    m.decision_count += 1
        except OSError:
            pass
        return m
