#!/usr/bin/env python3
# [C5-REAL] Sovereign Omni-Ultramap Swarm Controller
import os
import sys
import time
import json
import random
from pathlib import Path

# Insert cortex-persist into path
sys.path.insert(0, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist")

from cortex.engine.ultramap import UltramapSubstrate
from google import genai
from google.genai import types
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

console = Console()

def run_simulation():
    console.print(Panel.fit(
        "[bold #2B3BE5]ULTRAMAP-Ω[/bold #2B3BE5] [dim]x[/dim] [bold #00f3ff]GEMINI OMNI FLASH[/bold #00f3ff]\n"
        "[dim]Sovereign Swarm Endocrinology & Closed-Loop Cognitive Control[/dim]",
        border_style="#2B3BE5",
        subtitle="[C5-REAL Reality Level]"
    ))

    # Initialize the client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[bold red]ERROR:[/bold red] GEMINI_API_KEY not found in environment.")
        return

    client = genai.Client(api_key=api_key)
    
    # We will use gemini-2.5-flash as the real-time coordinator
    model_name = "gemini-2.5-flash"
    
    # 1. Initialize Topological Substrate (capacity=10 for simulation)
    umap = UltramapSubstrate(capacity=10)
    
    # Seed 5 agents
    agents_info = [
        {"idx": 0, "name": "k0_daemon_alpha", "target": "CVE-2026-MINIPLASMA"},
        {"idx": 1, "name": "k0_daemon_beta", "target": "TARGET_DARKPOOL_0x1"},
        {"idx": 2, "name": "k0_daemon_gamma", "target": "MEMBRANE_SHIELD_V3"},
        {"idx": 3, "name": "k0_daemon_delta", "target": "OUROBOROS_STRIKE_Ω"},
        {"idx": 4, "name": "k0_daemon_epsilon", "target": "SILICON_THERMAL_DISSIPATOR"}
    ]
    
    # Initialize random positions
    for a in agents_info:
        x = random.uniform(10.0, 90.0)
        y = random.uniform(10.0, 90.0)
        z = random.uniform(10.0, 90.0)
        umap.update_agent_position(a["idx"], x, y, z, a["target"], 0.5)
        umap.update_control_vector(a["idx"], 1.0, 0.0, 0.1, 0.2, source="genesis")

    console.print(f"[bold green]✔[/bold green] Substrate populated. File [dim]ultramap.bin[/dim] mapped in memory.")

    # Schema for structured JSON response from Gemini
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "agent_adjustments": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "agent_idx": types.Schema(type=types.Type.INTEGER),
                        "dx": types.Schema(type=types.Type.NUMBER),
                        "dy": types.Schema(type=types.Type.NUMBER),
                        "dz": types.Schema(type=types.Type.NUMBER),
                        "queue_depth": types.Schema(type=types.Type.NUMBER),
                        "error_rate": types.Schema(type=types.Type.NUMBER),
                        "causal_entropy": types.Schema(type=types.Type.NUMBER),
                        "cpu_load": types.Schema(type=types.Type.NUMBER),
                    },
                    required=["agent_idx", "dx", "dy", "dz", "queue_depth", "error_rate", "causal_entropy", "cpu_load"],
                )
            ),
            "rationale": types.Schema(type=types.Type.STRING),
        },
        required=["agent_adjustments", "rationale"]
    )
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=0.2
    )

    try:
        for step in range(1, 4):
            console.print(f"\n[bold #2B3BE5]── STEP {step} / 3 ───────────────────────────────────────────────────────────[/bold #2B3BE5]")
            
            # Fetch current state from memory-mapped bin
            states = []
            for a in agents_info:
                state = umap.get_agent_state(a["idx"])
                joules = umap.calculate_exergy_distance(a["idx"], a["target"])
                state["name"] = a["name"]
                state["exergy_joules"] = joules
                
                # Simulate hormone fields based on current state (Endocrinology decay)
                # Dopamine decays with distance to target, Cortisol increases with error_rate
                dist_to_target = (joules * state["entropy"])
                state["dopamine"] = max(0.0, 1.0 - (dist_to_target / 100.0))
                state["cortisol"] = min(1.0, state["error_rate"] * 2.0)
                states.append(state)

            # Generate the dashboard table
            table = Table(title=f"ULTRAMAP-Ω State Telemetry (Step {step})", title_style="bold #2B3BE5", show_header=True, header_style="bold white")
            table.add_column("Agent", style="cyan")
            table.add_column("Coordinates (X, Y, Z)", style="dim")
            table.add_column("Target", style="magenta")
            table.add_column("Exergy (Joules)", style="green")
            table.add_column("Dopamine (#00f3ff)", style="#00f3ff")
            table.add_column("Cortisol (#ff3333)", style="#ff3333")
            table.add_column("CPU / Queue", style="yellow")
            
            for s in states:
                table.add_row(
                    s["name"],
                    f"{s['x']:.2f}, {s['y']:.2f}, {s['z']:.2f}",
                    s["target"],
                    f"{s['exergy_joules']:.2f} J",
                    f"{s['dopamine']:.2f}",
                    f"{s['cortisol']:.2f}",
                    f"{s['cpu_load']*100:.1f}% / {s['queue_depth']:.0f}"
                )
            
            console.print(table)
            
            # Call Gemini Omni to act as the cognitive engine of the swarm
            console.print(f"[dim]Resolving swarm vectors with [bold #00f3ff]{model_name}[/bold #00f3ff]...[/dim]")
            
            prompt = (
                "You are the Sovereign Swarm Mind (Omni-K0 Controller). You are monitoring a topological agent memory substrate "
                "aligned to 128 bytes on physical silicon (ULTRAMAP-Ω).\n\n"
                f"Current Swarm State:\n{json.dumps(states, indent=2)}\n\n"
                "Determine the next movement vector (dx, dy, dz) to guide each agent toward its target destination (which is "
                "represented by the exergy distance). Also, adjust their control vectors (queue_depth, error_rate, causal_entropy, "
                "cpu_load) based on their current hormonal state (reduce queue_depth and CPU if cortisol is high, reward with higher "
                "efficiency if dopamine is high). Return your rationale in a short YAML string, along with the adjustments."
            )
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            
            # Parse response
            data = json.loads(response.text)
            
            # Print rationale
            console.print(Panel(
                Text(data.get("rationale", "").strip(), style="italic #00f3ff"),
                title="Omni-K0 Controller Rationale",
                border_style="#00f3ff"
            ))
            
            # Apply adjustments to the bin file
            for adj in data.get("agent_adjustments", []):
                idx = adj["agent_idx"]
                # Find matching agent info
                agent_meta = next((a for a in agents_info if a["idx"] == idx), None)
                if agent_meta is None:
                    continue
                
                # Get current position
                cur = umap.get_agent_state(idx)
                new_x = max(0.0, min(100.0, cur["x"] + adj["dx"]))
                new_y = max(0.0, min(100.0, cur["y"] + adj["dy"]))
                new_z = max(0.0, min(100.0, cur["z"] + adj["dz"]))
                
                # Recalculate new entropy based on causal_entropy
                new_entropy = max(0.01, min(1.0, adj["causal_entropy"]))
                
                # Mutate binary file position
                umap.update_agent_position(idx, new_x, new_y, new_z, agent_meta["target"], new_entropy)
                
                # Mutate control vectors
                umap.update_control_vector(
                    idx,
                    queue_depth=adj["queue_depth"],
                    error_rate=adj["error_rate"],
                    causal_entropy=adj["causal_entropy"],
                    cpu_load=adj["cpu_load"],
                    source="omni_controller"
                )
                
            console.print(f"[bold green]✔[/bold green] Swarm mutations written to memory substrate. Lock-free transaction complete.")
            time.sleep(1)

    finally:
        umap.close()
        console.print("\n[bold green]✔[/bold green] ULTRAMAP-Ω connection safely closed. Cache synced to disk.")

if __name__ == "__main__":
    run_simulation()
