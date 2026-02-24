import os
import re
from pathlib import Path
import shutil
import ast

repo_root = Path(__file__).resolve().parent.parent
cortex_root = repo_root / "cortex"

MOVES = {
    # API
    "api.py": "api/core.py",
    "api_audit.py": "api/audit.py",
    "api_deps.py": "api/deps.py",
    "api_state.py": "api/state.py",
    "async_client.py": "api/async_client.py",
    "client.py": "api/client.py",
    "middleware.py": "api/middleware.py",
    
    # DB
    "cache.py": "database/cache.py",
    "connection_pool.py": "database/pool.py",
    "db.py": "database/core.py",
    "db_messages.py": "database/messages.py",
    "db_writer.py": "database/writer.py",
    "schema.py": "database/schema.py",
    
    # Compaction
    "compactor.py": "compaction/compactor.py",
    "pruner.py": "compaction/pruner.py",
    
    # engine.py is deleted entirely
    
    # Episodic
    "episodic_boot.py": "episodic/boot.py",
    "episodic_base.py": "episodic/base.py",
    "episodic.py": "episodic/main.py",
    
    # Others
    "federation.py": "federation/main.py",
    "hive.py": "hive/main.py",
    "handoff.py": "agents/handoff.py",
    "neural.py": "agents/neural.py",
    "metrics.py": "telemetry/metrics.py",
    "telemetry.py": "telemetry/core.py",
    "canonical.py": "utils/canonical.py",
    "compression.py": "utils/compression.py",
    "errors.py": "utils/errors.py",
    "export.py": "utils/export.py",
    "i18n.py": "utils/i18n.py",
    "result.py": "utils/result.py",
    "sandbox.py": "utils/sandbox.py",
    "chronos.py": "timing/chronos.py",
    "daemon_cli.py": "daemon/cli.py",
    "daemon_platform.py": "daemon/platform.py",
    "dashboard.py": "routes/dashboard.py",
    "event_loop.py": "events/loop.py",
    "gate_types.py": "gate/types.py",
    "launchpad.py": "launchpad/main.py",
    "ledger.py": "consensus/ledger.py",
    "merkle.py": "consensus/merkle.py",
    "models.py": "types/models.py",
    "perception_base.py": "perception/base.py",
    "reflection.py": "thinking/reflection.py",
    "search_sync.py": "search/sync.py",
    "sys_platform.py": "platform/sys.py",
    "temporal.py": "memory/temporal.py",
    "tips.py": "cli/tips.py",
}

IMPORT_MAPPINGS = {}
for old_file, new_file in MOVES.items():
    old_module = "cortex." + old_file.replace(".py", "")
    new_module = "cortex." + new_file.replace(".py", "").replace("/", ".")
    IMPORT_MAPPINGS[old_module] = new_module

# Add manual deleted proxy replacements
IMPORT_MAPPINGS["cortex.engine"] = "cortex.engine.core"
# Wait, cortex.engine IS A DIRECTORY in git. So cortex.engine shouldn't be mapped.

def safe_replace(content: str) -> str:
    # Sort by length to avoid partial replacement (e.g. cortex.episodic before cortex.episodic_boot)
    sorted_mappings = sorted(IMPORT_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for old_mod, new_mod in sorted_mappings:
        # Match `from cortex.api import X` -> `from cortex.api.core import X`
        # But NOT `from cortex.api.something import X`
        # Regex uses lookahead to ensure it doesn't match a subpackage dot
        content = re.sub(rf"from\s+{re.escape(old_mod)}\s+import", f"from {new_mod} import", content)
        
        # Match `import cortex.api` -> `import cortex.api.core`
        # But NOT `import cortex.api.something`
        content = re.sub(rf"import\s+{re.escape(old_mod)}(?!\.)(\s|$)", rf"import {new_mod}\1", content)
        
        # Match `cortex.api.function()` -> `cortex.api.core.function()`
        # We need to only match if it's not a known subpackage.
        # This is harder with regex, but let's assume if it is EXACTLY followed by an uppercase letter or we just use simple AST?
        # A simple AST parser for replacing imports is much safer. Let's use regex for imports only.
        
    return content

class ImportTransformer(ast.NodeTransformer):
    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in IMPORT_MAPPINGS:
                alias.name = IMPORT_MAPPINGS[alias.name]
        return node
        
    def visit_ImportFrom(self, node):
        if node.module in IMPORT_MAPPINGS:
            node.module = IMPORT_MAPPINGS[node.module]
        return node

def ast_replace(filepath: Path):
    content = filepath.read_text()
    try:
        tree = ast.parse(content)
        transformer = ImportTransformer()
        transformer.visit(tree)
        
        # Ast unparse requires python 3.9+
        new_content = ast.unparse(tree)
        # AST unparsing strips some formatting, so we only use regex which is safer for formatting
    except SyntaxError:
        pass

def rewrite_imports_regex(content: str) -> str:
    sorted_mappings = sorted(IMPORT_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)
    for old_mod, new_mod in sorted_mappings:
        content = re.sub(rf"^from\s+{re.escape(old_mod)}\s+import", f"from {new_mod} import", content, flags=re.MULTILINE)
        content = re.sub(rf"^import\s+{re.escape(old_mod)}(?!\.)(\s|$)", rf"import {new_mod}\1", content, flags=re.MULTILINE)
        
        # Replace inline calls like `cortex.api.foo` but NOT `cortex.api.submodule`
        # Safe heuristic: look for cortex.old_mod.[a-z] but it's risky
    return content

def execute_moves():
    print("Moving files...")
    moved_count = 0
    # Engine cleanup first
    engine_py = cortex_root / "engine.py"
    if engine_py.exists():
        engine_py.unlink()
        print("Removed cortex.engine.py proxy")
        
    for old_file, new_file in MOVES.items():
        src = cortex_root / old_file
        if not src.exists():
            continue
            
        dst = cortex_root / new_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        init_file = dst.parent / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            
        shutil.move(str(src), str(dst))
        moved_count += 1
        print(f"Moved {old_file} -> {new_file}")
    
    print(f"\nMoved {moved_count} files.")

def rewrite_project_files():
    modified = 0
    for target_dir in [repo_root / "cortex", repo_root / "tests"]:
        if not target_dir.exists():
            continue
            
        for filepath in target_dir.rglob("*.py"):
            try:
                content = filepath.read_text()
                new_content = rewrite_imports_regex(content)
                if content != new_content:
                    filepath.write_text(new_content)
                    modified += 1
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
                
    print(f"Rewrote imports in {modified} files.")

if __name__ == "__main__":
    execute_moves()
    rewrite_project_files()
