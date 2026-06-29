# [C5-REAL] Exergy-Maximized
"""
cat_id: build-swarm-mapping
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

from pathlib import Path

import yaml


def main():
    workspace = Path(__file__).parent.parent.resolve()
    agents_dir = workspace / "babylon60" / "extensions" / "agents" / "definitions"
    out_path = workspace / "docs" / "design" / "LEGION_93_MAPPING.md"
    
    agents = []
    
    for f in sorted(agents_dir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as file:
                data = yaml.safe_load(file)
            
            meta = data.get("metadata", {})
            name = data.get("name", "UNKNOWN")
            model = data.get("model", "UNKNOWN")
            provider = data.get("provider", "UNKNOWN")
            intent = data.get("intent", "UNKNOWN")
            
            agents.append({
                "cat_id": meta.get("cat_id", f.stem),
                "name": name,
                "exergy": meta.get("exergy_tier", "N/A"),
                "reality": meta.get("reality_level", "N/A"),
                "intent": intent,
                "provider": provider,
                "model": model
            })
        except Exception as e:
            print(f"Error parsing {f.name}: {e}")
            
    # Sort by exergy then by cat_id
    agents.sort(key=lambda x: (x["exergy"], x["cat_id"]))
    
    # Generate markdown
    md = [
        "---",
        "cat_id: legion-93-mapping",
        "cat_type: architecture",
        "version: 1.0.0",
        "reality_level: C5-REAL",
        "owner: borjamoskv",
        "---\n",
        "# C5-REAL TENSOR: Exhaustive Swarm Mapping (LEGION-93)\n",
        "> **\"CERO ANERGÍA ES LA MUERTE.\"** — Cristalizado bajo autoridad de Borja Moskv (Γ1)\n",
        "Matriz topológica absoluta. Mapeo exhaustivo de las entidades agénticas en el ecosistema BABYLON-60.\n",
        "| ID Nodo (`cat_id`) | Identidad Cognitiva | Exergy | Realidad | Intent | Provider | Payload (Modelo) |",
        "|:---|:---|:---:|:---:|:---|:---|:---|"
    ]
    
    for a in agents:
        md.append(f"| **{a['cat_id']}** | {a['name']} | {a['exergy']} | {a['reality']} | `{a['intent']}` | `{a['provider']}` | `{a['model']}` |")
        
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md), encoding="utf-8")
    
    print(f"Generated exhaustive mapping for {len(agents)} agents at {out_path.relative_to(workspace)}.")

if __name__ == "__main__":
    main()
