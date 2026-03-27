"""Soul Store (Ω₁) — Apotheosis Core Persistence.

This module handles the persistence of 'Souls' (agent configuration, 
memory signatures, and identity markers) to the filesystem.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("cortex.soul")

class SoulStore:
    """Persistence layer for Agent Souls."""
    
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        
    async def persist(self, project: str, content: dict | str):
        """Persist soul data for a project."""
        target = self.root / f"{project}.json"
        
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                content = {"raw": content}
                
        with open(target, "w") as f:
            json.dump(content, f, indent=2)
            
        logger.info("Soul persisted for project %s at %s", project, target)
        
    async def retrieve(self, project: str) -> dict | None:
        """Retrieve soul data for a project."""
        target = self.root / f"{project}.json"
        if not target.exists():
            return None
            
        with open(target) as f:
            return json.load(f)
