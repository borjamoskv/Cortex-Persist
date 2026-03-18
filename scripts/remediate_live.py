import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.database.core import BUSY_TIMEOUT_MS
from cortex.engine.core import AsyncCortexEngine
from cortex.extensions.swarm.remediation.engine import LegionRemediationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("remediation_live.log")
    ]
)

logger = logging.getLogger("cortex.remediate_live")

async def main():
    db_path = str(Path("~/.cortex/cortex.db").expanduser())
    
    if not Path(db_path).exists():
        logger.error(f"Database not found at {db_path}")
        return

    logger.info("--- LEGION REMEDIATION RELEASE: PRODUCTION EXECUTION ---")
    logger.info(f"Target Database: {db_path}")
    logger.info(f"Busy Timeout: {BUSY_TIMEOUT_MS}ms")
    
    # Initialize CortexEngine for functional fixes
    cortex_engine = AsyncCortexEngine(db_path)
    await cortex_engine.initialize()

    # Initialize implementation engine
    # dry_run=False means it WILL mutate the database
    engine = LegionRemediationEngine(
        db_path=db_path,
        dry_run=False,
        engine=cortex_engine
    )

    try:
        logger.info("Starting Remediation Swarm (100 agents)...")
        report = await engine.execute()
        
        # Summary report
        logger.info("--- REMEDIATION REPORT SUMMARY ---")
        logger.info(f"Total Scanned: {report.total_facts_scanned}")
        logger.info(f"Issues Found: {report.total_issues_found}")
        logger.info(f"Successfully Applied: {report.fixes_applied}")
        logger.info(f"Rejected by Red Team: {report.fixes_rejected}")
        logger.info(f"Failed Execution: {report.fixes_failed}")
        
        report_file = "remediation_report_live.json"
        engine.save_report(report, report_file)
        logger.info(f"Full report saved to {report_file}")
        
        if report.failed_count > 0:
            logger.warning(f"Detected {report.failed_count} failures. Check logs for database lock errors.")
            
    except Exception as e:
        logger.error(f"Remediation swarm collapsed: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Remediation interrupted by user.")
