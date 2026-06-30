import json
from collections import defaultdict

collisions = defaultdict(list)
primitives = []

with open('babylon60/agents/primitives/ONTOLOGIA_BLUEPRINT_1000.jsonl', 'r') as f:
    for line in f:
        p = json.loads(line)
        primitives.append(p)
        # Group by exact name
        collisions[p['name']].append(p['id'])

report = []
for name, ids in collisions.items():
    if len(ids) > 1:
        report.append({
            "name": name,
            "ids": ids,
            "count": len(ids)
        })

report.sort(key=lambda x: x['count'], reverse=True)

with open('babylon60/agents/primitives/COLLISION_REPORT.json', 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"Found {len(report)} exact name collisions across domains.")
