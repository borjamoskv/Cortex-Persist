# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Signal Hook — fact:stored reactive emission.

Every call to ``engine.store()`` emits a ``fact:stored`` signal into
the persistent Signal Bus (L1 consciousness layer).  The emission is:

- **Invisible** to the operator: never raises, never blocks the store.
- **Non-blocking**: uses a fire-and-forget pattern via a direct sync
  write to the *separate* signals table (different connection object).
- **Self-healing**: if the bus table hasn't been created yet, it is
  bootstrapped on the first emission.
- **Reactive seeds**: the payload carries enough context for downstream
  consumers (``compact``, ``export``) to act autonomously:

  ``fact:stored`` payload schema::

      {
        "fact_id":    int,         # ID of the newly persisted fact
        "project":    str,         # Project scope
        "fact_type":  str,         # decision | error | ghost | knowledge …
        "source":     str,         # Originating agent / tool
        "tenant_id":  str,         # Isolation scope (default → "default")
        "total_facts": int | None, # Live count (None if query fails)
      }

Compact auto-trigger threshold
-------------------------------
When the count of *unconsumed* ``fact:stored`` signals for a given
project exceeds ``COMPACT_TRIGGER_THRESHOLD``, a single ``compact:needed``
signal is also emitted so that a listening daemon (``cortex compact``) or
a future L2 reactor can auto-execute compaction without human intervention.
This is the *neural seed* of L2 reactivity: the first emit() is invisible,
the second is a consequence — the system develops reflexes.
"""

from __future__ import annotations

import logging
import sqlite3

__all__ = ["emit_fact_stored"]

logger = logging.getLogger("cortex.signals.fact_hook")

# ── Tuneable constants ────────────────────────────────────────────────────────
# Number of un-consumed fact:stored signals before a compact:needed is emitted.
# Operators may override via env var CORTEX_COMPACT_THRESHOLD.
_DEFAULT_COMPACT_THRESHOLD: int = 50


def _compact_threshold() -> int:
    import os
    raw = os.environ.get("CORTEX_COMPACT_THRESHOLD", "")
    try:
        v = int(raw)
        return v if v > 0 else _DEFAULT_COMPACT_THRESHOLD
    except ValueError:
        return _DEFAULT_COMPACT_THRESHOLD


def emit_fact_stored(
    db_path: str,
    fact_id: int,
    project: str,
    fact_type: str,
    source: str,
    tenant_id: str = "default",
    total_facts: int | None = None,
) -> None:
    """Fire-and-forget emission of ``fact:stored`` into the Signal Bus.

    Opens its own *separate* sync sqlite3 connection to the signals table
    so that it never pollutes or blocks the engine's aiosqlite session.

    Args:
        db_path:     Absolute path to the main CORTEX DB.
        fact_id:     ID returned by the store operation.
        project:     Project the fact belongs to.
        fact_type:   Type label (decision, error, ghost …).
        source:      Originating tool / agent identity.
        tenant_id:   Tenant isolation scope.
        total_facts: Optional live count of active facts for this project
                     (passed in to avoid a double read inside this hook).
    """
    try:
        from cortex.signals.bus import SignalBus

        conn = sqlite3.connect(db_path, timeout=3)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        bus = SignalBus(conn)
        bus.ensure_table()

        payload: dict = {
            "fact_id": fact_id,
            "project": project,
            "fact_type": fact_type,
            "source": source,
            "tenant_id": tenant_id,
        }
        if total_facts is not None:
            payload["total_facts"] = total_facts

        bus.emit(
            "fact:stored",
            payload,
            source=source or "engine:store",
            project=project,
        )

        # ── Reactive Auto-Trigger: compact:needed ─────────────────────────
        # Count unconsumed fact:stored signals for this project.
        # If they exceed the threshold, emit compact:needed so a daemon
        # can act without human intervention — the L2 neural seed.
        threshold = _compact_threshold()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM signals "
                "WHERE event_type = 'fact:stored' "
                "AND project = ? "
                "AND consumed_by = '[]'",
                (project,),
            )
            row = cursor.fetchone()
            unconsumed = row[0] if row else 0

            if unconsumed >= threshold:
                bus.emit(
                    "compact:needed",
                    {
                        "project": project,
                        "unconsumed_fact_signals": unconsumed,
                        "threshold": threshold,
                        "reason": (
                            f"{unconsumed} un-consumed fact:stored signals "
                            f"exceeded threshold ({threshold})"
                        ),
                    },
                    source="fact-hook",
                    project=project,
                )
                logger.info(
                    "compact:needed emitted for project=%s (unconsumed=%d)",
                    project,
                    unconsumed,
                )
        except sqlite3.Error as e:
            logger.debug("compact:needed check failed: %s", e)

        conn.close()

    except sqlite3.Error as e:
        # Never propagate — this hook must never break the store operation.
        logger.debug("fact:stored signal emission failed (sqlite): %s", e)
    except ImportError as e:
        logger.debug("fact:stored signal emission failed (import): %s", e)
    except Exception as e:  # noqa: BLE001 — intentional catch-all for safety net
        logger.debug("fact:stored signal emission failed (unexpected): %s", e)
