# [C5-REAL] Exergy-Maximized
"""
Structural Arbitrage Extension (Asymmetric Arbitrage Daemon)
Exploits asymmetric market inefficiencies with industrial precision.
"""

from cortex.extensions.structural_arbitrage.daemon import ArbitrageDaemon
from cortex.extensions.structural_arbitrage.kernel import ExecutionKernel
from cortex.extensions.structural_arbitrage.models import ArbitrageSignal, CortexAmount
from cortex.extensions.structural_arbitrage.scanner import InefficiencyScanner

__all__ = [
    "ArbitrageDaemon",
    "ArbitrageSignal",
    "CortexAmount",
    "ExecutionKernel",
    "InefficiencyScanner",
]
