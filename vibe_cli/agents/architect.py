class ArchitectAgent:
    def run(self, state):
        dependency_graph = {}
        for file, structure in state.code_structure.items():
            dependency_graph[file] = structure.get("imports", [])

        state.dependency_graph = dependency_graph

        # Detect modules
        modules = set()
        for file in state.files:
            parts = file.replace("\\", "/").split("/")
            if len(parts) > 1:
                modules.add(parts[-2])

        # Count totals
        total_classes = sum(len(s.get("classes", [])) for s in state.code_structure.values())
        total_functions = sum(len(s.get("functions", [])) for s in state.code_structure.values())

        # Coupling analysis
        coupling = {}
        for file, imports in dependency_graph.items():
            coupling[file] = len(imports)

        # High coupling
        high_coupling = {f: c for f, c in coupling.items() if c >= 8}

        # Orphans
        orphans = [f for f, imps in dependency_graph.items() if len(imps) == 0]

        state.current_architecture = {
            "modules_detected": sorted(modules),
            "total_classes": total_classes,
            "total_functions": total_functions,
            "files_analyzed": len(state.code_structure),
            "high_coupling_files": high_coupling,
            "possible_orphans": orphans[:20]
        }

        # Simple architecture inference
        if state.stack.get("python") and state.stack.get("react"):
            state.recommended_architecture = {"pattern": "Frontend / Backend Separation", "backend": "Python", "frontend": "React"}
        elif total_classes > total_functions:
            state.recommended_architecture = {"pattern": "OOP / Layered"}
        else:
            state.recommended_architecture = {"pattern": "Functional / Script-based"}

        # Mermaid Graph Generation
        mermaid_lines = ["```mermaid", "graph TD;"]
        for file, imports in dependency_graph.items():
            source = file.split('/')[-1].replace('.', '_').replace('-', '_')
            if not imports:
                mermaid_lines.append(f"    {source};")
            for imp in imports:
                target = imp.replace('.', '_').replace('-', '_')
                mermaid_lines.append(f"    {source} --> {target};")
        mermaid_lines.append("```")
        
        state.current_architecture["mermaid_graph"] = "\n".join(mermaid_lines)

        return state
