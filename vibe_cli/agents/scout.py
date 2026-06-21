from pathlib import Path

class ScoutAgent:
    def run(self, state):
        root = Path(state.root_path)
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in [".py", ".js", ".ts", ".tsx", ".md", ".json"]:
                state.files.append(str(path))

        state.stack = {
            "python": any(f.endswith(".py") for f in state.files),
            "node": any("package.json" in f for f in state.files),
            "react": any(f.endswith(".tsx") for f in state.files),
            "markdown_docs": any(f.endswith(".md") for f in state.files)
        }
        return state
