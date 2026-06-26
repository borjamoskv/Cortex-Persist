import re
import json
import yaml
import os

skill_path = "/Users/borjafernandezangulo/.gemini/config/skills/MOSKV1-Arsenal-OMEGA/SKILL.md"
output_dir = "/Users/borjafernandezangulo/30_CORTEX/.agents/primitives"

with open(skill_path, "r", encoding="utf-8") as f:
    content = f.read()

primitives = []
# Matches something like: ### APEX-001 · Name
pattern = re.compile(r"###\s+(APEX-\d{3})\s+·\s+(.*?)\n(.*?)(?=\n###|\Z)", re.DOTALL)

for match in pattern.finditer(content):
    apex_id = match.group(1).strip()
    name = match.group(2).strip()
    body = match.group(3).strip()
    
    primitive = {
        "id": apex_id,
        "name": name,
        "trigger": "",
        "execute": "",
        "verify": "",
        "fail": ""
    }
    
    for line in body.split('\n'):
        if line.startswith("- **Trigger:**"):
            primitive["trigger"] = line.replace("- **Trigger:**", "").strip()
        elif line.startswith("- **Execute:**"):
            primitive["execute"] = line.replace("- **Execute:**", "").strip()
        elif line.startswith("- **Verify:**"):
            primitive["verify"] = line.replace("- **Verify:**", "").strip()
        elif line.startswith("- **Fail:**"):
            primitive["fail"] = line.replace("- **Fail:**", "").strip()
            
    primitives.append(primitive)

# Save JSON registry
registry_json = os.path.join(output_dir, "APEX_REGISTRY.json")
with open(registry_json, "w", encoding="utf-8") as f:
    json.dump({"primitives": primitives}, f, indent=2, ensure_ascii=False)

# Save YAML registry
registry_yaml = os.path.join(output_dir, "APEX_REGISTRY.yaml")
with open(registry_yaml, "w", encoding="utf-8") as f:
    yaml.dump({"primitives": primitives}, f, allow_unicode=True, default_flow_style=False)

# Create a Markdown Index
registry_md = os.path.join(output_dir, "APEX_INDEX.md")
with open(registry_md, "w", encoding="utf-8") as f:
    f.write("# MOSKV-1 APEX PRIMITIVES REGISTRY (C5-REAL)\n\n")
    for p in primitives:
        f.write(f"## {p['id']} · {p['name']}\n")
        f.write(f"- **Trigger:** {p['trigger']}\n")
        f.write(f"- **Execute:** {p['execute']}\n")
        f.write(f"- **Verify:** {p['verify']}\n")
        f.write(f"- **Fail:** {p['fail']}\n\n")

print(f"Extracted {len(primitives)} primitives to {output_dir}")
