import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.database.pool import CortexConnectionPool
from cortex.engine.async_engine import AsyncCortexEngine
from cortex.extensions.swarm.remediation.engine import LegionRemediationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("remediation_live.log")],
)

logger = logging.getLogger("cortex.remediate_live")


async def main():
    db_path = str(Path("~/.cortex/cortex.db").expanduser())

    if not Path(db_path).exists():
        logger.error("Database not found at %s", db_path)
        return

    logger.info("--- LEGION REMEDIATION RELEASE: PRODUCTION EXECUTION ---")
    logger.info("Target Database: %s", db_path)
    # Initialize connection pool
    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()

    # Initialize CortexEngine for functional fixes
    cortex_engine = AsyncCortexEngine(pool, db_path)
    await cortex_engine.initialize()

    # Initialize implementation engine
    # dry_run=False means it WILL mutate the database
    engine = LegionRemediationEngine(db_path=db_path, dry_run=False, engine=cortex_engine)

    try:
        logger.info("Starting Remediation Swarm (100 agents)...")
        report = await engine.execute()

        # Summary report
        logger.info("--- REMEDIATION REPORT SUMMARY ---")
        logger.info("Total Scanned: %s", report.total_facts_scanned)
        logger.info("Issues Found: %s", report.total_issues_found)
        logger.info("Successfully Applied: %s", report.fixes_applied)
        logger.info("Rejected by Red Team: %s", report.fixes_rejected)
        logger.info("Failed Execution: %s", report.fixes_failed)

        report_file = "remediation_report_live.json"
        engine.save_report(report, report_file)
        logger.info("Full report saved to %s", report_file)

        if report.fixes_failed > 0:
            logger.warning(
                "Detected %s failures. Check logs for database lock errors.", report.fixes_failed
            )

    except Exception as e:
        logger.exception("Remediation swarm collapsed: %s", e)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Remediation interrupted by user.")
