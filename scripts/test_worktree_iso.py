import asyncio
import logging
import os
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_worktree")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cortex.extensions.swarm.worktree_isolation import isolated_worktree


async def test_isolation():
    branch = f"test_iso_{os.getpid()}"
    logger.info("Starting isolation test with branch: %s", branch)

    try:
        async with isolated_worktree(branch) as wt_path:
            logger.info("Inside isolated worktree: %s", wt_path)
            assert wt_path.exists(), "Worktree path should exist"

            # Check if we are in a different directory or can see the branch
            import subprocess

            res = subprocess.run(
                ["git", "branch", "--show-current"], cwd=wt_path, capture_output=True, text=True
            )
            logger.info("Current branch in worktree: %s", res.stdout.strip())
            assert res.stdout.strip() == branch, (
                f"Expected branch {branch}, got {res.stdout.strip()}"
            )

        logger.info("Exited isolated worktree context.")
        assert not wt_path.exists(), "Worktree path should be cleaned up"
        logger.info("Cleanup verified.")

    except Exception as e:
        logger.error("Test failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_isolation())
