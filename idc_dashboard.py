import time
import numpy as np
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import BarColumn, Progress, TextColumn
from rich.console import Console
from idc_core import IDCAgent

class IDCDashboard:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.setup_layout()

    def setup_layout(self):
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        self.layout["main"].split_row(
            Layout(name="info_pane"),
            Layout(name="decision_pane"),
            Layout(name="control_pane")
        )

    def generate_table(self, title, name, value, sub_metrics=None):
        table = Table(title=title, expand=True, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold yellow")
        table.add_row(name, f"{value:.4f}")
        if sub_metrics:
            for k, v in sub_metrics.items():
                table.add_row(f"  └─ {k}", str(v))
        return Panel(table, border_style="blue")

    def run_live(self):
        # Setup Agent & Env (Mirroring Sandbox)
        agent = IDCAgent(num_states=5, num_actions=3, constraints=[
            lambda a, s: -np.sum(s * np.log(s + 1e-12)) < 1.4 or a == 0
        ])
        L = np.eye(5) * 0.7 + 0.075
        U = np.zeros((3, 5))
        U[0, :] = [0, 0, 0, 0, 1] 
        U[1, :] = [0, 0.5, 0.5, 0.5, 0]
        U[2, :] = [0, 1, 1, 1, 0]

        true_state = 2
        
        with Live(self.layout, refresh_per_second=4, screen=True):
            for t in range(50):
                # Env step
                obs = true_state if np.random.rand() < 0.7 else np.random.randint(0, 5)
                action = agent.step(obs, L, U)
                
                # Update True State
                if action == 1: true_state = max(0, true_state - 1)
                elif action == 2: true_state = min(4, true_state + 1)

                # Update UI
                self.layout["header"].update(Panel(f"[bold white]IDC AGENT DASHBOARD[/] | Time Step: [yellow]{t}[/] | True State: [green]{true_state}[/]", border_style="green"))
                
                self.layout["info_pane"].update(self.generate_table(
                    "Layer 03: INFORMATION", "Entropy H(X)", agent.info.entropy, 
                    {"Last Obs": obs, "Belief Peak": f"S{np.argmax(agent.info.belief)}"}
                ))
                
                self.layout["decision_pane"].update(self.generate_table(
                    "Layer 02: DECISION", "Action Taken", action,
                    {"Strategy": "Thompson", "Proposed": action}
                ))
                
                self.layout["control_pane"].update(self.generate_table(
                    "Layer 01: CONTROL", "Stability Margin", agent.control.stability_margin,
                    {"Status": "STABLE" if agent.control.stability_margin > 0.8 else "CAUTION"}
                ))

                self.layout["footer"].update(Panel(f"Current Output: {['STAY', 'LEFT', 'RIGHT'][action]}", border_style="magenta"))
                
                time.sleep(0.5)

if __name__ == "__main__":
    db = IDCDashboard()
    db.run_live()
