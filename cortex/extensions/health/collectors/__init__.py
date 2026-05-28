# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""Built-in metric collectors."""

from cortex.extensions.health.collectors.db import DbCollector, DiskSpaceCollector, WalCollector
from cortex.extensions.health.collectors.ledger import LedgerCollector
from cortex.extensions.health.collectors.mnemonic import (
    EntropyCollector,
    FactCountCollector,
    SnapshotAgeCollector,
)
from cortex.extensions.health.collectors.system import OrphanedBrowserCollector, SystemLoadCollector

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
