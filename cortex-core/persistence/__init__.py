import sys
from pathlib import Path

from .base import (
    SovereignResource,
    _setup_sqlite_pragmas,
    DB_PATH,
    VSA_BIN_PATH,
    VSA_DIMENSION,
    HAS_CORTEX_RS,
    outbox_wake_event,
    ledger_entropy_event,
    _get_local_conn,
    logger,
    _metrics_cache,
    _metrics_cache_lock,
)
from .cache import ContextCache
from .ledger import LedgerManager
from .vsa import VSAMemory

import daemons.outbox

sys.modules["persistence.outbox"] = daemons.outbox
outbox = daemons.outbox
from daemons.outbox import (
    ZeroCopyRingBuffer,
    OutboxDaemon,
    enqueue_swarm_task,
    get_swarm_metrics,
    _get_ring_buffer,
)

from .ide_preserver import IdeStatePreserver

import daemons.security_recon

sys.modules["persistence.security_recon"] = daemons.security_recon
security_recon = daemons.security_recon
from daemons.security_recon import SecurityReconDaemon

from .hybrid import HybridPersistenceManager

# Lazy import: UltramapSubstrate lives one level up, resolve without sys.path mutation
_ultramap_parent = str(Path(__file__).resolve().parent.parent)
if _ultramap_parent not in sys.path:
    sys.path.insert(0, _ultramap_parent)
from ultramap import UltramapSubstrate

__all__ = [
    "SovereignResource",
    "_setup_sqlite_pragmas",
    "DB_PATH",
    "VSA_BIN_PATH",
    "VSA_DIMENSION",
    "HAS_CORTEX_RS",
    "outbox_wake_event",
    "ledger_entropy_event",
    "_get_local_conn",
    "logger",
    "ContextCache",
    "LedgerManager",
    "VSAMemory",
    "ZeroCopyRingBuffer",
    "OutboxDaemon",
    "enqueue_swarm_task",
    "get_swarm_metrics",
    "IdeStatePreserver",
    "SecurityReconDaemon",
    "HybridPersistenceManager",
    "_metrics_cache",
    "_metrics_cache_lock",
    "_get_ring_buffer",
    "UltramapSubstrate",
]
