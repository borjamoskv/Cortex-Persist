import pytest
import time
from click.testing import CliRunner
from cortex.cli import cli
from cortex.engine import CortexEngine

def test_single(tmp_path):
    path = tmp_path / "test.db"
    
    start = time.time()
    engine = CortexEngine(db_path=path)
    engine.init_db_sync()
    engine.store_sync("test-project", "First test fact", fact_type="knowledge", source="cli")
    engine.close_sync()
    print(f"Setup DB: {time.time() - start:.2f}s")

    runner = CliRunner()
    
    start = time.time()
    result = runner.invoke(cli, ["edit", "1", "Edited content", "--db", str(path)])
    print(f"Edit command: {time.time() - start:.2f}s")
    
    start = time.time()
    list_result = runner.invoke(cli, ["list", "--db", str(path), "-p", "test-project"])
    print(f"List command: {time.time() - start:.2f}s")

if __name__ == "__main__":
    pytest.main(["-v", "-s", "fix_test.py"])
