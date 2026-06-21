from pathlib import Path
from core.parser import CodeParser

class StructureAgent:
    def __init__(self):
        self.parser = CodeParser()

    def run(self, state):
        state.code_structure = {}
        for file in state.files:
            try:
                content = Path(file).read_text(errors="ignore")
                if file.endswith(".py"):
                    state.code_structure[file] = self.parser.parse_python(content)
                elif file.endswith((".js", ".ts", ".tsx", ".jsx")):
                    state.code_structure[file] = self.parser.parse_js(content)
            except:
                continue
        return state
