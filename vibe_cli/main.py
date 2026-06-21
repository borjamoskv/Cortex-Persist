import sys
import json
from pathlib import Path

from core.state import ProjectState
from conductor import VibeConductor


def generate_markdown(state):
    lines = []

    lines.append("# PROJECT CANON\n")

    lines.append("## Stack Detected")
    for k, v in state.stack.items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Architecture")
    for k, v in state.current_architecture.items():
        if k != "mermaid_graph":
            lines.append(f"- {k}: {v}")

    lines.append("\n## Recommended Architecture")
    for k, v in state.recommended_architecture.items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Features Detected")
    for f in state.features:
        lines.append(f"- {f['feature']} (source: {f['source']})")

    lines.append("\n## Tasks")
    for t in state.tasks:
        lines.append(f"- {t['title']} [{t['priority']}]")

    if "mermaid_graph" in state.current_architecture:
        lines.append("\n## Dependency Graph (Mermaid)")
        lines.append(state.current_architecture["mermaid_graph"])

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py /path/to/project")
        return

    project_path = sys.argv[1]

    state = ProjectState(root_path=project_path)
    conductor = VibeConductor()
    state = conductor.run(state)

    Path("outputs").mkdir(exist_ok=True)

    Path("outputs/STACK.json").write_text(json.dumps(state.stack, indent=2))
    Path("outputs/FEATURES.json").write_text(json.dumps(state.features, indent=2))
    Path("outputs/TASKS.json").write_text(json.dumps(state.tasks, indent=2))
    
    arch_json = {k:v for k,v in state.current_architecture.items() if k != "mermaid_graph"}
    Path("outputs/ARCHITECTURE.json").write_text(json.dumps(arch_json, indent=2))
    
    Path("outputs/DEPENDENCY_GRAPH.json").write_text(json.dumps(state.dependency_graph, indent=2))

    Path("outputs/PROJECT_CANON.md").write_text(generate_markdown(state))

    print("✅ Consolidation complete (no dependencies).")
    print("Outputs saved in /outputs")


if __name__ == "__main__":
    main()
