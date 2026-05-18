import re

with open("tests/test_crystal_consolidation.py", "r") as f:
    content = f.read()

content = content.replace('with patch("sqlite3.Connection.cursor", return_value=cursor_mock):', 'in_memory_db.cursor = MagicMock(return_value=cursor_mock)')
content = content.replace('with patch("sqlite3.Connection.commit", side_effect=sqlite3.Error("Mock error")):', 'in_memory_db.commit = MagicMock(side_effect=sqlite3.Error("Mock error"))')

with open("tests/test_crystal_consolidation.py", "w") as f:
    f.write(content)
