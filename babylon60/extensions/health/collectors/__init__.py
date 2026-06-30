# [C5-REAL] Exergy-Maximized

from babylon60.extensions.health.collectors.db import DbCollector, DiskSpaceCollector, WalCollector
from babylon60.extensions.health.collectors.ledger import LedgerCollector
from babylon60.extensions.health.collectors.mnemonic import (
    EntropyCollector,
    FactCountCollector,
    SnapshotAgeCollector,
)
from babylon60.extensions.health.collectors.system import OrphanedBrowserCollector, SystemLoadCollector

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
