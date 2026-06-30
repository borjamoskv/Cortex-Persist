from core.graph import detect_cycles
from core.patterns import detect_pattern
from core.routers import detect_routers


class ArchitectAgent:

    def run(self, state):

        dependency_graph = {}
        for file, structure in state.code_structure.items():
            dependency_graph[file] = structure.get("imports", [])

        state.dependency_graph = dependency_graph

        modules = set()
        for file in state.files:
            parts = file.replace("\\", "/").split("/")
            if len(parts) > 1:
                modules.add(parts[-2])

        total_classes = sum(
            len(s.get("classes", [])) for s in state.code_structure.values()
        )
        total_functions = sum(
            len(s.get("functions", [])) for s in state.code_structure.values()
        )

        coupling = {f: len(i) for f, i in dependency_graph.items()}
        high_coupling = {f: c for f, c in coupling.items() if c >= 8}

        orphans = [
            f for f, imps in dependency_graph.items() if len(imps) == 0
        ]

        cycles = detect_cycles(dependency_graph)
        routers = detect_routers(state.files)

        state.current_architecture = {
            "modules_detected": sorted(modules),
            "total_classes": total_classes,
            "total_functions": total_functions,
            "files_analyzed": len(state.code_structure),
            "high_coupling_files": high_coupling,
            "possible_orphans": orphans[:20],
            "dependency_cycles": cycles[:10],
            "routers_detected": routers
        }

        state.recommended_architecture = detect_pattern(state)

        return state
