"""
Sovereign AlphaZero CLI Commands.
"""

import click
from rich.console import Console
from rich.table import Table

from cortex.engine.alphazero.mcts_core import MCTS, AlphaZeroNode
from cortex.engine.alphazero.network import LocalHeuristicNetwork
from cortex.engine.alphazero.arc_env import ARCEnv, ARCState

console = Console()

@click.group(name="az")
def az_group():
    """Sovereign AlphaZero Autodidact-Ω commands."""
    pass

@az_group.command(name="train")
@click.argument("env_id", default="arc")
@click.option("--simulations", default=50, help="Number of MCTS simulations per step.")
def train_cmd(env_id: str, simulations: int):
    """
    Start a self-play training loop (AlphaZero /az-train).
    Currently defaults to ARC-AGI environment.
    """
    console.print(f"[bold blue]ALPHAZERO-AUTODIDACT-Ω[/bold blue]: Starting training on [green]{env_id}[/green]...")
    
    if env_id != "arc":
        console.print(f"[red]Error[/red]: Environment '{env_id}' not implemented.")
        return

    # 1. Setup Env and Network
    env = ARCEnv()
    network = LocalHeuristicNetwork(env)
    
    from cortex.agents.arc_agi_3.ingestion import GestaltNode, Pixel
    node = GestaltNode(id="n1", color=1, pixels={Pixel(0,0,1)}, bbox=(0,0,0,0))
    initial_state = ARCState(
        nodes=(node,), 
        rows=3, 
        cols=3, 
        background=0,
        step_count=0
    )
    
    mcts = MCTS(network, num_simulations=simulations)
    root = AlphaZeroNode(state=initial_state)
    
    # 3. Execution loop (single step demo)
    console.print(f"Running {simulations} MCTS simulations...")
    mcts.simulate(root, env)
    
    probs = mcts.get_action_probabilities(root)
    
    table = Table(title="Action Probabilities (MCTS)")
    table.add_column("Action", style="cyan")
    table.add_column("Probability", style="magenta")
    
    for action, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]:
        table.add_row(str(action), f"{prob:.4f}")
        
    console.print(table)
    console.print("[green]Success[/green]: MCTS loop completed successfully.")

@az_group.command(name="pit")
@click.argument("model_a")
@click.argument("model_b")
@click.argument("env_id", default="arc")
def pit_cmd(model_a: str, model_b: str, env_id: str):
    """
    Evaluate two models against each other (/az-pit).
    """
    console.print(f"[bold blue]ALPHAZERO-AUTODIDACT-Ω[/bold blue]: Pitting [cyan]{model_a}[/cyan] vs [magenta]{model_b}[/magenta] on {env_id}...")
    # Logic for tournament evaluation would go here
    console.print("Tournament logic pending full model persistence implementation.")
