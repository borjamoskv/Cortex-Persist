import ast
import logging
from cortex.engine.smte.parser import AgentASTParser
from cortex.guards.exergy_guard import ExergyGuard, calculate_exergy

logger = logging.getLogger("cortex.engine.smte.trigger")
logging.basicConfig(level=logging.INFO)

def docstring_mutator(tree: ast.AST) -> bool:
    """Adds a C5-REAL tag to the module docstring if not present."""
    changed = False
    
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        doc = tree.body[0].value.value
        if "C5-REAL MUTATED" not in doc:
            tree.body[0].value.value = doc + "\n\n[C5-REAL MUTATED BY SMTE]"
            changed = True
    else:
        doc_node = ast.Expr(value=ast.Constant(value="[C5-REAL MUTATED BY SMTE]"))
        tree.body.insert(0, doc_node)
        changed = True
        
    return changed

def run_mutation_cycle(target_path: str):
    parser = AgentASTParser(target_path)
    
    guard = ExergyGuard()
    initial_exergy = calculate_exergy(parser.source_code)
    logger.info(f"[*] Initial Exergy of {target_path}: {initial_exergy:.4f}")
    
    logger.info("[*] Applying AST Mutation...")
    if parser.apply_mutation(docstring_mutator):
        logger.info("[*] Mutation structurally sound. Crystallizing...")
        new_source = parser.crystallize()
        new_exergy = calculate_exergy(new_source)
        logger.info(f"[*] New Exergy: {new_exergy:.4f}")
        
        if new_exergy >= initial_exergy:
            logger.info("[+] Mutation ACCEPTED. Fitness improved or maintained.")
        else:
            logger.warning("[-] Mutation DEGRADED exergy, but committed for testing purposes.")
    else:
        logger.error("[-] Mutation structural check failed.")

if __name__ == "__main__":
    target = "cortex/engine/smte/__init__.py"
    run_mutation_cycle(target)
