import json
from pathlib import Path
from typing import List, Dict


class SpecialistRouter:
    """Sovereign Specialist Router (Ω₁ Scaling).

    Maps user missions and detected code signals to the most relevant
    specialists in the kimi-swarm-1.
    """

    def __init__(self, specialists_path: str = None):
        if not specialists_path:
            parent = Path(__file__).parent.parent
            specialists_path = str(parent / "resources" / "prompts" / "specialists.json")

        with open(specialists_path, "r") as f:
            data = json.load(f)
            self.specialists = data["specialists"]

    def route_mission(self, mission: str) -> List[Dict]:
        """Routes a mission string to a list of specialists based on keyword triggers."""
        mission_lower = mission.lower()
        selected = []

        # Priority: DataAlchemist if graph/sql tools are mentioned (Ω₁)
        for s in self.specialists:
            if any(trigger in mission_lower for trigger in s["triggers"]):
                selected.append(s)

        # Ω₁ Persistence: If DataAlchemist or graph analysis is involved, pair with LoreKeeper
        if any(s["id"] == "DataAlchemist" for s in selected):
            if not any(s["id"] == "LoreKeeper" for s in selected):
                lore_keeper = next((s for s in self.specialists if s["id"] == "LoreKeeper"), None)
                if lore_keeper:
                    selected.append(lore_keeper)

        # Fallback to ArchitectPrime + CodeNinja if nothing is caught
        if not selected:
            selected = [s for s in self.specialists if s["id"] in ["ArchitectPrime", "CodeNinja"]]

        return selected


if __name__ == "__main__":
    # Test routing
    router = SpecialistRouter()
    mission_text = "Analyze the impact graph of the last security decision using trace-impact"
    agents = router.route_mission(mission_text)
    print(f"Mission: {mission_text}")
    print(f"Selected Specialists: {[a['id'] for a in agents]}")
