# [C5-REAL] Exergy-Maximized
"""
cat_id: export-substack-nodes
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import json
import os
import sqlite3

cortex_dir = os.path.expanduser('~/30_CORTEX')
db_path = os.path.join(cortex_dir, 'cortex', 'audit', 'substack_exergy.sqlite')
output_json = os.path.join(cortex_dir, 'public', 'substack_nodes.json')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT post_id, title, date, wordcount, exergy_score, status FROM substack_nodes")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(rows)} nodes to {output_json}")
else:
    print("Database not found!")
