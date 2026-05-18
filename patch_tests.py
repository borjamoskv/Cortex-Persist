import re

with open("tests/test_crystal_consolidation.py", "r") as f:
    content = f.read()

content = content.replace('with patch("sqlite3.Connection.cursor", side_effect=sqlite3.Error("Mock error")):', 'cursor_mock = MagicMock()\n        cursor_mock.execute.side_effect = sqlite3.Error("Mock error")\n        cursor_mock.executemany.side_effect = sqlite3.Error("Mock error")\n        with patch.object(in_memory_db, "cursor", return_value=cursor_mock, create=True):')
content = content.replace('with patch("sqlite3.Connection.commit", side_effect=sqlite3.Error("Mock error")):', 'with patch.object(in_memory_db, "commit", side_effect=sqlite3.Error("Mock error"), create=True):')

with open("tests/test_crystal_consolidation.py", "w") as f:
    f.write(content)
