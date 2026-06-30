import json
import sys
from pathlib import Path

from conductor import VibeConductor
from core.health import score_project
from core.mermaid import generate_mermaid
from core.state import ProjectState


def generate_markdown(state, health):
    lines = []

    lines.append("# PROJECT CANON\n")

    lines.append(f"## Health Score: {health['score']}/100 {health['label']}\n")

    lines.append("### Penalties")
    for p in health["penalties"]:
        lines.append(f"- {p}")

    lines.append("\n### Bonuses")
    for b in health["bonuses"]:
        lines.append(f"- {b}")

    lines.append("\n## Stack Detected")
    for k, v in state.stack.items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Architecture Detected")
    for k, v in state.current_architecture.items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Recommended Architecture")
    rec = state.recommended_architecture
    lines.append(f"- Pattern: {rec.get('pattern')}")
    lines.append(f"- Confidence: {rec.get('confidence_score')}")

    lines.append("\n## Features Detected")
    for f in state.features:
        lines.append(f"- {f['feature']} (source: {f['source']})")

    lines.append("\n## Tasks")
    for t in state.tasks:
        lines.append(f"- {t['title']} [{t['priority']}]")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py /path/to/project")
        return

    project_path = sys.argv[1]

    state = ProjectState(root_path=project_path)
    conductor = VibeConductor()
    state = conductor.run(state)

    health = score_project(state)
    mermaid = generate_mermaid(state.dependency_graph)

    Path("outputs").mkdir(exist_ok=True)

    Path("outputs/STACK.json").write_text(
        json.dumps(state.stack, indent=2)
    )
    Path("outputs/FEATURES.json").write_text(
        json.dumps(state.features, indent=2)
    )
    Path("outputs/TASKS.json").write_text(
        json.dumps(state.tasks, indent=2)
    )
    Path("outputs/ARCHITECTURE.json").write_text(
        json.dumps(state.current_architecture, indent=2)
    )
    Path("outputs/DEPENDENCY_GRAPH.json").write_text(
        json.dumps(state.dependency_graph, indent=2)
    )
    Path("outputs/HEALTH.json").write_text(
        json.dumps(health, indent=2)
    )
    Path("outputs/DIAGRAM.md").write_text(
        f"```mermaid\n{mermaid}\n```"
    )
    Path("outputs/PROJECT_CANON.md").write_text(
        generate_markdown(state, health)
    )

    print("\n✅ Consolidation complete.")
    print(f"Health: {health['score']}/100 {health['label']}")
    print(f"Pattern: {state.recommended_architecture['pattern']}")
    print(f"Files analyzed: {state.current_architecture['files_analyzed']}")
    print(f"Functions found: {state.current_architecture['total_functions']}")
    print(f"Classes found: {state.current_architecture['total_classes']}")
    print("\nOutputs saved in /outputs")


if __name__ == "__main__":
    main()
