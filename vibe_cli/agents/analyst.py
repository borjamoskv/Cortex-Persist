from pathlib import Path

class AnalystAgent:
    def run(self, state):
        for file in state.files[:100]:  # limit for speed
            try:
                content = Path(file).read_text(errors="ignore")[:3000]
                state.summaries[file] = content
                lc = content.lower()
                if "auth" in lc or "login" in lc:
                    state.features.append({"feature": "authentication", "source": file})
                if "payment" in lc or "checkout" in lc:
                    state.features.append({"feature": "payments", "source": file})
                if "agent" in lc:
                    state.features.append({"feature": "agent_system", "source": file})
                if "todo" in lc:
                    state.technical_debt.append({"type": "TODO_found", "file": file})
            except:
                continue
        return state
