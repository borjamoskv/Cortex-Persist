import re

with open("tests/test_crystal_consolidation.py", "r") as f:
    content = f.read()

content = content.replace('with patch.object(in_memory_db, "cursor", return_value=cursor_mock, create=True):', 'with patch.object(in_memory_db, "cursor", return_value=cursor_mock):')
content = content.replace('with patch.object(in_memory_db, "commit", side_effect=sqlite3.Error("Mock error"), create=True):', 'with patch.object(in_memory_db, "commit", side_effect=sqlite3.Error("Mock error")):')

with open("tests/test_crystal_consolidation.py", "w") as f:
    f.write(content)
