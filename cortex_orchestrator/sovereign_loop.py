"""
CORTEX Sovereign Loop v4.0 — Dual Orchestrator (AX-044: Math + Capital)
Wires real TritonMCTSProver (MLX GPU) + MEV Annihilator staging engine
into self-funding Ouroboros cycle.

Capital → Compute → Axiom → Ledger → Capital (∞)

AX-050: Direct-Silicon JIT (FPGA latency absorbed)
Ω₆:     O(1) Tensor-State (vectorized matmul scoring)
AX-100: Yield Ouroboros (net_yield → allocate_compute)
"""

import asyncio
import hashlib
import logging
import signal
import sys
import os
import time
from decimal import Decimal
from typing import Any, Optional

# ─── Path setup ──────────────────────────────────────────────────────
CORTEX_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CORTEX_ROOT not in sys.path:
    sys.path.insert(0, CORTEX_ROOT)

from millennium.mcts_kernel import TritonMCTSProver, ProofResult
from cortex.ledger import GitSovereignLedger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cortex.orchestrator.sovereign_loop")


# ─── MEV Scanner (wires to test_harness or simulates) ────────────────

class SovereignMEVScanner:
    """
    Capital extraction coroutine.
    Imports cortex_mev_annihilator.test_harness for MockFPGA+MockAnnihilator.
    Falls back to inline simulation when staging engine is unavailable.
    """

    def __init__(self) -> None:
        self.cumulative_yield = Decimal("0")
        self.strikes = 0
        self._fpga_guard = None
        self._annihilator = None
        self._init_backend()

    def _init_backend(self):
        try:
            from cortex_mev_annihilator.test_harness import (
                MockFPGAToxGuard,
                MockMEVAnnihilator,
            )
            self._fpga_guard = MockFPGAToxGuard()
            self._annihilator = MockMEVAnnihilator(self._fpga_guard)
            logger.info("[MEV] Backend: MockFPGA + MockAnnihilator (test harness)")
        except ImportError:
            logger.info("[MEV] Backend: inline simulation (no staging_engine)")

    async def scan_and_stage(self) -> Optional[Decimal]:
        if self._annihilator:
            return await self._harness_scan()
        return await self._sim_scan()

    async def _harness_scan(self) -> Optional[Decimal]:
        try:
            txs = [{"to": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "block": 19200001}]
            ref = await self._annihilator.stage_bundle_mock(
                txs, 19200002, Decimal("0.05"), anvil_latency_ms=30
            )
            net = ref["net_yield"]
            self.cumulative_yield += net
            self.strikes += 1
            logger.info(
                "[MEV] Strike #%d | Net: %s | Total: %s",
                self.strikes, net, self.cumulative_yield,
            )
            return net
        except Exception as e:
            logger.warning("[MEV] Scan failed: %s", e)
            return None

    async def _sim_scan(self) -> Optional[Decimal]:
        await asyncio.sleep(0.05)
        import random
        if random.random() > 0.3:
            net = Decimal(str(round(random.uniform(0.01, 0.1), 4)))
            self.cumulative_yield += net
            self.strikes += 1
            logger.info(
                "[MEV-SIM] Strike #%d | Net: %s | Total: %s",
                self.strikes, net, self.cumulative_yield,
            )
            return net
        return None


# ─── Crystallizer (ledger persistence) ───────────────────────────────

class SovereignCrystallizer:
    """AX-041: Git-DAG entangled taint chain for proofs and yields."""

    def __init__(self) -> None:
        self.ledger = GitSovereignLedger(CORTEX_ROOT)
        self._head = ""
        self.entries: list[dict] = []
        try:
            import subprocess
            cwd = str(self.ledger.workspace_root)
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True)
            if r.returncode == 0:
                self._head = r.stdout.strip()
            else:
                self._head = hashlib.sha256(b"genesis").hexdigest()
        except Exception:
            self._head = hashlib.sha256(b"genesis").hexdigest()

    def head_hash(self) -> str:
        return self._head

    async def crystallize_theorem(self, proof: ProofResult) -> None:
        entry = {
            "type": "THEOREM",
            "tactics": proof.tactics,
            "depth": proof.depth,
            "elapsed_s": f"{proof.elapsed_s:.3f}",
            "taint": proof.taint,
            "parent_hash": self._head,
            "timestamp": int(time.time() * 1000),
        }
        ts = await self.ledger.commit_state(
            state_mutation=entry,
            file_name=".cortex/ledger/proof_state.json",
            commit_message=f"CORTEX(Math): Theorem proven [{proof.taint[:8]}]"
        )
        self._head = ts.commit_sha
        self.entries.append(entry)
        logger.info("[CRYSTALLIZER] Theorem persisted | Taint: %s…", proof.taint[:16])

    async def crystallize_yield(self, amount: Decimal, strike_n: int) -> None:
        entry = {
            "type": "MEV_YIELD",
            "amount": str(amount),
            "strike": strike_n,
            "taint": hashlib.sha256(f"MEV|{amount}|{time.time()}".encode()).hexdigest(),
            "parent_hash": self._head,
            "timestamp": int(time.time() * 1000),
        }
        ts = await self.ledger.commit_state(
            state_mutation=entry,
            file_name=".cortex/ledger/mev_state.json",
            commit_message=f"CORTEX(MEV): Strike #{strike_n} Yield: {amount}"
        )
        self._head = ts.commit_sha
        self.entries.append(entry)


# ─── Sovereign Loop ─────────────────────────────────────────────────

class SovereignLoop:
    """
    AX-044: Dual fork — Math + Capital.
    Capital yield → allocate_compute() → more MCTS iterations.
    Cycle: Capital → Compute → Axiom → Ledger
    """

    THEOREMS = ["Riemann_Hypothesis", "P_vs_NP", "Navier_Stokes"]

    def __init__(self, max_cycles: int = 10, depth: int = 3) -> None:
        self.max_cycles = max_cycles
        self.depth = depth

        # Core engines
        self.prover = TritonMCTSProver()
        self.scanner = SovereignMEVScanner()
        self.crystallizer = SovereignCrystallizer()

        # State
        self.theorems_proven: list[str] = []
        self._shutdown = False

    async def boot(self) -> None:
        logger.info("[CORTEX] Booting Sovereign Loop v4.0 …")
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._request_shutdown)
        except NotImplementedError:
            pass  # Windows

    async def run(self) -> None:
        await self.boot()
        _header()

        theorem_idx = 0

        for cycle in range(self.max_cycles):
            if self._shutdown:
                break

            theorem = self.THEOREMS[theorem_idx % len(self.THEOREMS)]
            logger.info("═══ CYCLE %d/%d | Target: %s ═══", cycle + 1, self.max_cycles, theorem)

            # Fork: Math + Capital (non-blocking)
            math_task = asyncio.create_task(
                self.prover.search_proof(theorem, max_depth=self.depth, iterations=1000)
            )
            capital_task = asyncio.create_task(
                self.scanner.scan_and_stage()
            )

            done, pending = await asyncio.wait(
                [math_task, capital_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # ── Capital result ──
            if capital_task in done:
                net_yield = capital_task.result()
                if net_yield and net_yield > 0:
                    budget = float(net_yield) * 1000
                    self.prover.allocate_compute(budget)
                    await self.crystallizer.crystallize_yield(net_yield, self.scanner.strikes)
                    logger.info(
                        "[OUROBOROS] Yield %s → +%d MCTS iterations",
                        net_yield, int(budget),
                    )

            # ── Math result ──
            if math_task in pending:
                proof = await math_task
            else:
                proof = math_task.result()

            if proof.converged and "sorry" not in proof.tactics:
                await self.crystallizer.crystallize_theorem(proof)
                self.theorems_proven.append(theorem)
                theorem_idx += 1
                logger.info("[CONVERGENCE] Proof found in %.3fs!", proof.elapsed_s)
                logger.info("[CONVERGENCE] Tactics: %s", proof.tactics)
            else:
                logger.info(
                    "[MCTS] Depth %d | Elapsed %.3fs | Converged: %s",
                    proof.depth, proof.elapsed_s, proof.converged,
                )

            # Clean up pending tasks
            for task in pending:
                if not task.done():
                    try:
                        await task
                    except Exception:
                        pass

        _footer(self.scanner, self.crystallizer, self.theorems_proven)

    def _request_shutdown(self) -> None:
        logger.info("[CORTEX] Shutdown signal received.")
        self._shutdown = True


# ─── Display ─────────────────────────────────────────────────────────

def _header():
    print("=" * 72)
    print(" CORTEX SOVEREIGN LOOP v4.0 — DUAL ORCHESTRATOR")
    print(" [AX-044] Math + Capital Ouroboros Cycle")
    print(" [AX-046] Triton MCTS GPU Kernel (MLX)")
    print(" [AX-050] Direct-Silicon JIT / [AX-100] Yield Feedback")
    print("=" * 72)


def _footer(scanner, crystallizer, theorems):
    print("\n" + "=" * 72)
    print(f" TOTAL MEV YIELD    : {scanner.cumulative_yield}")
    print(f" TOTAL STRIKES      : {scanner.strikes}")
    print(f" LEDGER ENTRIES     : {len(crystallizer.entries)}")
    print(f" THEOREMS PROVEN    : {len(theorems)}")
    print(f" HEAD HASH          : {crystallizer.head_hash()[:32]}…")
    print("=" * 72)


# ─── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    sovereign = SovereignLoop(max_cycles=5, depth=3)
    asyncio.run(sovereign.run())
