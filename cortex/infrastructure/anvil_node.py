import asyncio
import logging

logger = logging.getLogger("cortex.infrastructure.anvil")


class AnvilStagingNode:
    """
    AX-050: Direct-Silicon JIT Pre-Flight Staging.
    Manages a deterministic local execution environment (Anvil) for 
    high-exergy validation prior to Crystallizer Commit.
    """

    def __init__(self, rpc_url: str | None = None, port: int = 8545):
        self.rpc_url = rpc_url
        self.port = port
        self.process: asyncio.subprocess.Process | None = None
        self.endpoint = f"http://127.0.0.1:{self.port}"
        
    async def start(self) -> None:
        """Ignites the Anvil staging node for pre-flight simulation."""
        logger.info("[ANVIL] Booting staging node on port %d...", self.port)
        cmd = f"anvil -p {self.port}"
        if self.rpc_url:
            cmd += f" --fork-url {self.rpc_url}"
            
        self.process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Allowance for structural readiness
        await asyncio.sleep(2)
        logger.info("[ANVIL] Staging node active at %s.", self.endpoint)
        
    async def stop(self) -> None:
        """Collapses the staging environment."""
        if self.process:
            logger.info("[ANVIL] Terminating staging node...")
            self.process.terminate()
            await self.process.wait()
            self.process = None
            logger.info("[ANVIL] Staging node terminated.")
