
from ultramap import UltramapSubstrate

from .base import DB_PATH

try:
    import cortex_rs  # noqa: F401
except ImportError:
    pass

from .cache import ContextCache
from .vsa import VSAMemory
from .ledger import LedgerManager
from daemons.outbox import ZeroCopyRingBuffer, OutboxDaemon
from .ide_preserver import IdeStatePreserver
from daemons.security_recon import SecurityReconDaemon
class HybridPersistenceManager:
    """
    Sovereign Hybrid Persistence Manager.
    Integrates L1 (RAM Context), L2 (Semantic VSA/SQLite), and L3 (Cryptographic Audit Ledger).
    """

    def __init__(self):
        self.l1 = ContextCache()
        self.l2 = VSAMemory()
        self.l3 = LedgerManager()
        self.ring = ZeroCopyRingBuffer()  # L4 Zero-Copy Substrate
        self.ultramap = UltramapSubstrate() # L5 Sovereign Topological Space
        self.ide_guardian = IdeStatePreserver(self.l3)
        self.outbox = OutboxDaemon(DB_PATH, ledger=self.l3)
        self.security_radar = SecurityReconDaemon(self.l3)
        self.ide_guardian.start_guardian()
        self.outbox.start_guardian()
        self.security_radar.start_guardian()

    def get_system_health(self) -> dict:
        """Aggregates C5-REAL telemetry from all persistence substrates."""
        return {
            "outbox": self.outbox.get_health_metrics(),
            "ledger_yield": self.l3.get_total_yield(),
        }


