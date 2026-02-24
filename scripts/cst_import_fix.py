import os
import pathlib
import libcst as cst
from libcst.matchers import *

module_moves = {
    "api" : "api.core",
    "api_audit": "api.audit",
    "api_deps": "api.deps",
    "api_state": "api.state",
    "async_client": "api.async_client",
    "client": "api.client",
    "middleware": "api.middleware",
    "cache": "database.cache",
    "connection_pool": "database.pool",
    "db": "database.core",
    "db_messages": "database.messages",
    "db_writer": "database.writer",
    "schema": "database.schema",
    "compactor": "compaction.compactor",
    "pruner": "compaction.pruner",
    "episodic_boot": "episodic.boot",
    "episodic_base": "episodic.base",
    "episodic": "episodic.main",
    "federation": "federation.main",
    "hive": "hive.main",
    "handoff": "agents.handoff",
    "neural": "agents.neural",
    "metrics": "telemetry.metrics",
    "telemetry": "telemetry.core",
    "canonical": "utils.canonical",
    "compression": "utils.compression",
    "errors": "utils.errors",
    "export": "utils.export",
    "i18n": "utils.i18n",
    "result": "utils.result",
    "sandbox": "utils.sandbox",
    "chronos": "timing.chronos",
    "daemon_cli": "daemon.cli",
    "daemon_platform": "daemon.platform",
    "event_loop": "events.loop",
    "gate_types": "gate.types",
    "launchpad": "launchpad.main",
    "ledger": "consensus.ledger",
    "merkle": "consensus.merkle",
    "models": "types.models",
    "perception_base": "perception.base",
    "reflection": "thinking.reflection",
    "search_sync": "search.sync",
    "sys_platform": "platform.sys",
    "temporal": "memory.temporal",
    "tips": "cli.tips",
    "dashboard": "routes.dashboard"
}

class ImportFixer(cst.CSTTransformer):
    def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom):
        if hasattr(updated_node.module, "value") and updated_node.module.value == "cortex":
            if isinstance(updated_node.names, cst.ImportStar):
                return updated_node
            
            new_imports = []
            kept_names = []
            
            for alias in updated_node.names:
                name = alias.name.value
                if name in module_moves:
                    new_mod = module_moves[name]
                    final_name = alias.asname.name.value if alias.asname else name
                    
                    new_imports.append(cst.Import(names=[cst.ImportAlias(
                        name=cst.parse_expression("cortex." + new_mod),
                        asname=cst.AsName(name=cst.Name(final_name)) if final_name != "cortex." + new_mod else None
                    )]))
                else:
                    kept_names.append(alias)
            
            res = []
            if kept_names:
                res.append(updated_node.with_changes(names=tuple(kept_names)))
            res.extend(new_imports)
            
            if len(res) == 1:
                return res[0]
            elif len(res) > 1:
                return cst.FlattenSentinel(res)
                
        if updated_node.module:
            try:
                mod_str = cst.helpers.get_full_name_for_node(updated_node.module)
                if mod_str and mod_str.startswith("cortex."):
                    parts = mod_str.split('.')
                    if len(parts) == 2 and parts[1] in module_moves:
                        new_mod = "cortex." + module_moves[parts[1]]
                        return updated_node.with_changes(module=cst.parse_expression(new_mod))
            except Exception:
                pass

        return updated_node

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import):
        new_names = []
        for alias in updated_node.names:
            try:
                name_str = cst.helpers.get_full_name_for_node(alias.name)
                if name_str.startswith("cortex."):
                    parts = name_str.split('.')
                    if len(parts) == 2 and parts[1] in module_moves:
                        new_mod = "cortex." + module_moves[parts[1]]
                        asname = alias.asname
                        if not asname:
                            asname = cst.AsName(name=cst.Name(parts[1]))
                        new_names.append(cst.ImportAlias(name=cst.parse_expression(new_mod), asname=asname))
                        continue
            except Exception:
                pass
            new_names.append(alias)
        return updated_node.with_changes(names=tuple(new_names))

def process_file(path):
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    
    try:
        tree = cst.parse_module(code)
    except Exception as e:
        print(f"Parse error in {path}: {e}")
        return
        
    wrapper = cst.MetadataWrapper(tree)
    modified_tree = wrapper.visit(ImportFixer())
    
    new_code = modified_tree.code
    if new_code != code:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_code)
        print(f"Fixed imports in {path}")

if __name__ == "__main__":
    import sys
    base = pathlib.Path(__file__).parent.parent
    for d in [base / "cortex", base / "tests"]:
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".py"):
                    process_file(os.path.join(root, f))
