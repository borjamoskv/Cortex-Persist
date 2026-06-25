# [C5-REAL] Exergy-Maximized

from legacy_research.extensions.health.collectors.db import DbCollector, DiskSpaceCollector, WalCollector
from legacy_research.extensions.health.collectors.ledger import LedgerCollector
from legacy_research.extensions.health.collectors.mnemonic import (
    EntropyCollector,
    FactCountCollector,
    SnapshotAgeCollector,
)
from legacy_research.extensions.health.collectors.system import OrphanedBrowserCollector, SystemLoadCollector

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
