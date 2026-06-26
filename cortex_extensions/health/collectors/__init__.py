# [C5-REAL] Exergy-Maximized

from cortex_extensions.health.collectors.db import DbCollector, DiskSpaceCollector, WalCollector
from cortex_extensions.health.collectors.ledger import LedgerCollector
from cortex_extensions.health.collectors.mnemonic import (
    EntropyCollector,
    FactCountCollector,
    SnapshotAgeCollector,
)
from cortex_extensions.health.collectors.system import OrphanedBrowserCollector, SystemLoadCollector

BUILTINS = [
    DbCollector,
    LedgerCollector,
    EntropyCollector,
    FactCountCollector,
    WalCollector,
    SystemLoadCollector,
    OrphanedBrowserCollector,
    SnapshotAgeCollector,
    DiskSpaceCollector,
]
