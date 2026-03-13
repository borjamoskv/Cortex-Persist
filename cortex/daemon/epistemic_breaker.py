import asyncio
import logging
import random

from cortex.utils.time import now_utc

logger = logging.getLogger(__name__)

class EpistemicBreakerDaemon:
    """
    Sovereign Epistemic Circuit Breaker (Axiom Ω₂ & Ω₃).
    
    Acts as the cognitive immune system for the Moskv-1 Daemon.
    Monitors the 'thermal noise' (semantic entropy, database growth, error rates).
    If the derivative of entropy (dE/dt) exceeds a threshold, it forces the system 
    into a 'Sleep Mode' (Circuit Open) to purge useless connections, compress memory, 
    and prevent the collapse of the causal graph.
    """
    
    def __init__(
        self,
        engine,
        check_interval_seconds: int = 300,
        max_entropy_threshold: float = 0.85,
    ):
        self.engine = engine
        self.check_interval_seconds = check_interval_seconds
        self.max_entropy_threshold = max_entropy_threshold
        self.is_running = False
        
        # Internal state to track entropy derivative
        self._last_fact_count = 0
        self._last_error_count = 0
        self._last_evaluation_time = now_utc()
        
        # System State
        self.circuit_open = False  # False = System is awake and acting. True = Sleep/Compressing.

    async def _measure_entropy(self) -> float:
        """
        Calculates the current cognitive entropy (0.0 to 1.0).
        In a real scenario, this queries the DB for rapid fact insertion rates,
        unlinked ghosts, or contradiction spikes.
        For now, we simulate a metric based on hypothetical DB stats and random noise.
        """
        # Placeholder query: how many 'error' or 'contradiction' facts recently?
        # In a full CORTEX DB, we'd query via self.engine
        pass
        
        # Simulate entropy metric. Under normal load it's low. Sometimes it spikes.
        # This will be replaced by actual deterministic O(1) metrics from the DB.
        simulated_noise = random.uniform(0.1, 0.4)
        
        # Let's say if the system is running "hot", noise increases.
        return simulated_noise

    async def _trigger_sleep_cycle(self):
        """
        The Circuit Breaker trips. The system must sleep to survive.
        (Axiom Ω₂: Entropic Asymmetry - Reduce entropy).
        """
        logger.warning("🔴 [EPISTEMIC BREAKER] CIRCUIT OPEN (TRIPPED). System entering mandatory sleep cycle.")
        self.circuit_open = True
        
        # Record the event in the sovereign ledger for auditing (Falla Bizantina)
        try:
            from cortex.facts.fact import AddFactRequest
            req = AddFactRequest(
                project="cortex-core",
                fact_type="decision",
                content="Epistemic limit crossed. Initiating cognitive shutdown and compression.",
                tags=["system", "immune", "circuit-breaker"],
                confidence="C5",
                source="agent:epistemic-breaker"
            )
            await self.engine.store(req)
        except Exception as e:
            logger.error("Failed to record breaker trip: %s", e)

        logger.info("🧠 [SLEEP CYCLE] Running Autodidact Compression / Memory Compaction... (Simulating structural prune)")
        
        # TODO: Call actual `compaction` module or `autodidact-omega` to reduce H(X)
        await asyncio.sleep(5)  # Simulate deep sleep and compression time
        
        logger.info("🟢 [EPISTEMIC BREAKER] Compression complete. Entropy reduced. CLOSING CIRCUIT.")
        self.circuit_open = False
        
        # Record wakeup
        try:
            from cortex.facts.fact import AddFactRequest
            req = AddFactRequest(
                project="cortex-core",
                fact_type="decision",
                content="Sleep cycle complete. Cognitive clarity restored. System resuming.",
                tags=["system", "immune", "circuit-breaker", "wakeup"],
                confidence="C5",
                source="agent:epistemic-breaker"
            )
            await self.engine.store(req)
        except Exception:
            pass


    async def run(self):
        """Main evaluation loop."""
        logger.info(f"🛡️ Epistemic Breaker Daemon Initialized. Scanning every {self.check_interval_seconds}s. Max Entropy limit: {self.max_entropy_threshold}")
        self.is_running = True
        
        while self.is_running:
            try:
                # 1. Measure the current state of chaos
                entropy = await self._measure_entropy()
                
                # We can also simulate an artificial spike to test it occasionally
                if random.random() > 0.95:
                    logger.warning("🌩️ Simulated Neural Storm detected. Artificial entropy spike.")
                    entropy = 0.99
                
                if entropy >= self.max_entropy_threshold:
                    logger.critical(
                        "⚠️ HIGH ENTROPY DETECTED: %.3f >= %.3f", 
                        entropy, 
                        self.max_entropy_threshold
                    )
                    # 2. If it exceeds limits, trip the breaker.
                    await self._trigger_sleep_cycle()
                else:
                    logger.debug("Epistemic load nominal: %.3f", entropy)

            except Exception as e:
                logger.error("Error in Epistemic Breaker loop: %s", e)
            
            # Wait for next scan, adjust if circuit is currently open
            if self.is_running:
                await asyncio.sleep(self.check_interval_seconds)

    def stop(self):
        """Signals the daemon to shut down cleanly."""
        logger.info("Stopping Epistemic Breaker Daemon...")
        self.is_running = False
