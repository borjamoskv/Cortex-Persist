import re

with open("tests/test_crystal_consolidation.py", "r") as f:
    content = f.read()

content = content.replace('        in_memory_db.cursor = MagicMock(return_value=cursor_mock)\n            await _execute_cold_purge(in_memory_db, vitals, result, dry_run=False)', '        in_memory_db.cursor = MagicMock(return_value=cursor_mock)\n        await _execute_cold_purge(in_memory_db, vitals, result, dry_run=False)')
content = content.replace('        in_memory_db.cursor = MagicMock(return_value=cursor_mock)\n            await _execute_semantic_merge(in_memory_db, vitals, result, dry_run=False)', '        in_memory_db.cursor = MagicMock(return_value=cursor_mock)\n        await _execute_semantic_merge(in_memory_db, vitals, result, dry_run=False)')
content = content.replace('        in_memory_db.commit = MagicMock(side_effect=sqlite3.Error("Mock error"))\n            await _execute_semantic_merge(in_memory_db, vitals, result, dry_run=False)', '        in_memory_db.commit = MagicMock(side_effect=sqlite3.Error("Mock error"))\n        await _execute_semantic_merge(in_memory_db, vitals, result, dry_run=False)')
content = content.replace('        in_memory_db.cursor = MagicMock(return_value=cursor_mock)\n            await _execute_diamond_promotion(in_memory_db, vitals, result, dry_run=False)', '        in_memory_db.cursor = MagicMock(return_value=cursor_mock)\n        await _execute_diamond_promotion(in_memory_db, vitals, result, dry_run=False)')

with open("tests/test_crystal_consolidation.py", "w") as f:
    f.write(content)
