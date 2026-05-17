import re

with open('cortex/extensions/swarm/crystal_consolidator.py', 'r') as f:
    content = f.read()

# Make sure updated_at is properly initialized to fix the sqlite query in synthesize
content = content.replace("UPDATE facts_meta SET content = ?, updated_at = ? WHERE id = ?", "UPDATE facts_meta SET content = ? WHERE id = ?")

# Since we modified the SQL, we need to modify the parameters in execute as well
content = content.replace("cursor.execute(\n                            \"UPDATE facts_meta SET content = ? WHERE id = ?\",\n                            (new_content, time.time(), id_a),\n                        )", "cursor.execute(\n                            \"UPDATE facts_meta SET content = ? WHERE id = ?\",\n                            (new_content, id_a),\n                        )")

with open('cortex/extensions/swarm/crystal_consolidator.py', 'w') as f:
    f.write(content)
