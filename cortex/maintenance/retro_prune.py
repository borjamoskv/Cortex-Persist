import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("cortex.maintenance.prune")

class RetroactiveLedgerPruner:
    """
    V5: Entropy Asymmetry Fix
    Scans the skills/ directory and prunes agents/skills 
    that haven't been invoked in >90 days, moving them to cold_forge.
    """
    def __init__(self, workspace_path: str):
        self.skills_dir = Path(workspace_path) / ".gemini/antigravity/skills"
        self.cold_forge_dir = Path(workspace_path) / "cold_forge"
        
    def execute_prune(self, active_skills_from_ledger: set):
        if not self.skills_dir.exists():
            return
            
        self.cold_forge_dir.mkdir(exist_ok=True)
        
        pruned_count = 0
        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir() and skill_path.name not in active_skills_from_ledger:
                logger.info(f"Pruning dead agent skill: {skill_path.name} -> Sortu/Cold Forge")
                shutil.move(str(skill_path), str(self.cold_forge_dir / skill_path.name))
                pruned_count += 1
                
        logger.info(f"Retroactive prune complete. {pruned_count} ghost agents compressed.")
