class PlannerAgent:
    def run(self, state):
        for debt in state.technical_debt:
            state.tasks.append({
                "title": f"Resolve TODO in {debt['file']}",
                "priority": "medium"
            })

        if state.stack.get("python") and state.stack.get("node"):
            state.tasks.append({
                "title": "Document frontend-backend integration",
                "priority": "high"
            })

        state.tasks.append({
            "title": "Generate clean canonical README",
            "priority": "high"
        })

        return state
