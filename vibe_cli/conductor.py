from agents.scout import ScoutAgent
from agents.structure import StructureAgent
from agents.analyst import AnalystAgent
from agents.architect import ArchitectAgent
from agents.planner import PlannerAgent

class VibeConductor:
    def __init__(self):
        self.scout = ScoutAgent()
        self.structure = StructureAgent()
        self.analyst = AnalystAgent()
        self.architect = ArchitectAgent()
        self.planner = PlannerAgent()

    def run(self, state):
        state = self.scout.run(state)
        state = self.structure.run(state)
        state = self.analyst.run(state)
        state = self.architect.run(state)
        state = self.planner.run(state)
        return state
