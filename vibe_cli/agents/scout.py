from pathlib import Path


class ScoutAgent:
    def run(self, state):
        root = Path(state.root_path)

        for path in root.rglob("*"):
            if path.is_file() and path.suffix in [".py", ".js", ".ts", ".tsx", ".md", ".json", ".yaml", ".yml"]:
                state.files.append(str(path))

        state.stack = {
            "python": any(f.endswith(".py") for f in state.files),
            "node": any("package.json" in f for f in state.files),
            "react": any(f.endswith(".tsx") for f in state.files),
            "fastapi": False,
            "django": False,
            "express": False,
            "nextjs": False,
            "markdown_docs": any(f.endswith(".md") for f in state.files)
        }

        # Detect frameworks por contenido rápido
        for f in state.files:
            if f.endswith(".py"):
                try:
                    content = Path(f).read_text(errors="ignore")[:2000]
                    if "from fastapi" in content or "import fastapi" in content:
                        state.stack["fastapi"] = True
                    if "from django" in content or "import django" in content:
                        state.stack["django"] = True
                except Exception:
                    pass

            if f.endswith(".json") and "package.json" in f:
                try:
                    content = Path(f).read_text(errors="ignore")
                    if "next" in content:
                        state.stack["nextjs"] = True
                    if "express" in content:
                        state.stack["express"] = True
                except Exception:
                    pass

        return state
