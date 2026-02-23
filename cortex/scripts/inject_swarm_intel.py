import json
import re
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent.parent

print("Inyectando nodos mule a los sistemas...")

with open(_PROJECT_ROOT / "swarm_graph.json") as f:
    graph = json.load(f)

new_nodes_from_swarm = list(graph.keys())

# --- PANOPTICON ---
panopticon_path = str(_SCRIPTS_DIR / "monitor_panopticon.py")
with open(panopticon_path) as f:
    content = f.read()

existing_nodes = set(n.lower() for n in re.findall(r'"(0x[a-fA-F0-9]{40})"', content))
mules_to_add = [n for n in new_nodes_from_swarm if n.lower() not in existing_nodes]

if mules_to_add:
    print(f"Adding {len(mules_to_add)} mules to Panopticon...")
    mules_str = "\n".join([f'    "{n}", # Swarm L4-L5 Mule' for n in mules_to_add])

    # Insert before the closing bracket of TARGET_WALLETS
    pattern = r"(TARGET_WALLETS\s*=\s*\[)(.*?)(\n\])"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        new_content = (
            content[: match.end(2)]
            + "\n    # --- INYECTADO POR LEGIØN-1 (Capa Profunda) ---\n"
            + mules_str
            + content[match.start(3) :]
        )
        with open(panopticon_path, "w") as f:
            f.write(new_content)
        print("Panopticon updated.")

# --- DOXX GLOBAL ---
doxx_path = str(_SCRIPTS_DIR / "doxxeo_global" / "DoxxGlobal.js")
with open(doxx_path) as f:
    content_doxx = f.read()

existing_nodes_doxx = set(n.lower() for n in re.findall(r'"(0x[a-fA-F0-9]{40})"', content_doxx))
mules_to_add_doxx = [n for n in new_nodes_from_swarm if n.lower() not in existing_nodes_doxx]

if mules_to_add_doxx:
    print(f"Adding {len(mules_to_add_doxx)} mules to DoxxGlobal...")
    mules_str_doxx = "\n".join([f'    "{n}", // Swarm L4-L5 Mule' for n in mules_to_add_doxx])

    pattern_doxx = r"(const COMPROMISED_WALLETS\s*=\s*\[)(.*?)(\n\];)"
    match_doxx = re.search(pattern_doxx, content_doxx, re.DOTALL)
    if match_doxx:
        new_content_doxx = (
            content_doxx[: match_doxx.end(2)]
            + "\n    // --- INYECTADO POR LEGIØN-1 (Capa Profunda) ---\n"
            + mules_str_doxx
            + content_doxx[match_doxx.start(3) :]
        )
        with open(doxx_path, "w") as f:
            f.write(new_content_doxx)
        print("DoxxGlobal updated.")

print("Inyección completada.")
