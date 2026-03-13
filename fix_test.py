import re
from pathlib import Path

path = Path("tests/genesis/test_genesis_engine.py")
content = path.read_text()

to_remove = """# All tests use /tmp to avoid polluting the real codebase
_TEST_ROOT = Path("/tmp/genesis_test_workspace")


@pytest.fixture(autouse=True)
def clean_workspace() -> None:
    \"\"\"Ensure clean workspace before each test.\"\"\"
    if _TEST_ROOT.exists():
        shutil.rmtree(_TEST_ROOT)
    _TEST_ROOT.mkdir(parents=True, exist_ok=True)
    yield  # type: ignore[misc]
    # Cleanup after test
    if _TEST_ROOT.exists():
        shutil.rmtree(_TEST_ROOT)"""

replacement = """@pytest.fixture
def test_root(tmp_path: Path) -> Path:
    \"\"\"Isolated workspace for each test.\"\"\"
    return tmp_path / "genesis_test_workspace\""""

content = content.replace(to_remove, replacement)

lines = content.split('\n')
for i in range(len(lines)):
    if lines[i].strip().startswith("def test_") and "(self)" in lines[i]:
        for j in range(i+1, len(lines)):
            if lines[j].strip().startswith("def ") or lines[j].strip().startswith("class "):
                break
            if "_TEST_ROOT" in lines[j]:
                lines[i] = lines[i].replace("(self)", "(self, test_root: Path)")
                break

content = "\n".join(lines).replace("_TEST_ROOT", "test_root")
path.write_text(content)
