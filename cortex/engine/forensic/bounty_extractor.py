# [C5-REAL] Exergy-Maximized
import asyncio
import logging

from cortex.darknet.ingestor import DarknetIngestor
from cortex.engine.forensic.forensic_commander import ForensicCommander
from cortex.engine.forensic.forensic_strike_config import MissionProfile

logger = logging.getLogger("bounty_extractor")


class BountyExergyExtractor:
    """
    Automated Bounty Hunter.
    Ingests OSINT vulnerability data, translates it to MissionProfiles,
    and dispatches a specialized Forensic Strike to extract Exergy.
    """

    def __init__(self, target_source: str = "immunefi"):
        self.target_source = target_source
        self.ingestor = DarknetIngestor()

    async def run(self) -> dict:
        """Executes the extraction pipeline."""
        logger.info("📡 [BOUNTY-RADAR] Initializing Quantitative Bounty Scanner...")
        
        # 1. Darknet Ingestion
        raw_data = await self.ingestor.ingest_cycle()
        
        # 2. Filter target source
        bounty_targets = [d for d in raw_data if d.source_type == self.target_source]
        
        if not bounty_targets:
            logger.warning("No bounties detected for source %s.", self.target_source)
            return {"status": "no_targets", "yield": 0.0}
            
        logger.info("💎 [BOUNTY-RADAR] Found %d actionable bounties.", len(bounty_targets))
        
        # 3. Create dynamic missions
        commander = ForensicCommander(strike_id=f"BOUNTY-STRIKE-{self.target_source.upper()}")
        commander.missions.clear()  # Overwrite static STRIKE_V1 missions
        
        for idx, target in enumerate(bounty_targets):
            mission_name = f"Bounty-{target.source_id}"
            
            # Extract target repo name safely from URL if possible, or use title
            repo_heuristic = target.url.split("/")[-1] if "/" in target.url else "unknown"
            
            mission = MissionProfile(
                name=mission_name,
                target_repo=f"bounty-targets/{repo_heuristic}",
                agent_density=1000,  # Focus 1k agents per bounty
                focus_areas=[target.title],
                priority=10, # Top priority
                intent="bounty_poc", # Thermodynamic yield inversion!
            )
            commander.missions[mission_name] = mission
            
        # 4. Dispatch the Strike
        logger.info("🚀 [BOUNTY-RADAR] Dispatching %d specialized missions.", len(commander.missions))
        await commander.initialize_strike()
        await commander.execute_mission_dispatch()
        
        # 5. Synthesize yield
        report = await commander.synthesize_audit_report()
        logger.info("🔥 [BOUNTY-RADAR] Extraction Strike Crystallized. Report: %s", report)
        
        return report
