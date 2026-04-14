import json
from pathlib import Path


def generate_legion_10k():
    registry = {
        "version": "2.0.0",
        "name": "CORTEX-LEGION-10K",
        "hierarchy": "L0-L4",
        "legions": {
            "SILVER": {"domain": "Audit", "centurions": 10},
            "GOLD": {"domain": "Wealth", "centurions": 10},
            "LEAD": {"domain": "Lore", "centurions": 10},
            "VOID": {"domain": "Defense", "centurions": 10},
            "SOVEREIGN": {"domain": "Governance", "centurions": 10},
            "SILICON": {"domain": "Hardware", "centurions": 10},
            "SONIC": {"domain": "Production", "centurions": 10},
            "OMNISCIENCE": {"domain": "Ingest", "centurions": 10},
            "SIMULATION": {"domain": "Chaos", "centurions": 10},
            "ETHICS": {"domain": "Alignment", "centurions": 10},
        },
        "centurions": [],
    }

    # Generate 100 Centurions (High-capacity Tactical Nodes)
    # Each Centurion manages 10 Vessels (L3), each with 10 Specialists (L4)
    for legion_name in registry["legions"]:
        for i in range(10):
            cen_id = f"CEN-{legion_name}-{i:02d}"
            registry["centurions"].append(
                {
                    "id": cen_id,
                    "legion": legion_name,
                    "vessels": 10,
                    "specialists_per_vessel": 10,
                    "genetic_parameters": {
                        "fitness": 1.0,
                        "ghost_density": 0.01,
                        "mutation_rate": 0.05,
                        "exergy_threshold": 0.4,
                    },
                }
            )

    output_path = Path("/Users/borjafernandezangulo/30_CORTEX/resources/swarm_10k_registry.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(registry, indent=2))
    print(f"✅ Fractal Registry 10k generated at {output_path}")


if __name__ == "__main__":
    generate_legion_10k()
