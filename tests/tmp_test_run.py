import sys
from click.testing import CliRunner
from cortex.cli import cli

runner = CliRunner()
db_path = sys.argv[1] if len(sys.argv) > 1 else "test.db"
# Wait, let's create a minimal test.db first
from cortex.engine import CortexEngine
engine = CortexEngine(db_path=db_path)
engine.init_db_sync()
engine.store_sync("test-project", "First test fact for CORTEX validation", fact_type="knowledge")
engine.store_sync("other-project", "Third test fact for ghost registering", fact_type="ghost")
engine.close_sync()

result = runner.invoke(cli, ["list", "--db", db_path, "--type", "ghost"])
print("EXIT CODE:", result.exit_code)
print("OUTPUT:")
print(result.output)
if result.exception:
    print("EXCEPTION:")
    import traceback
    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
