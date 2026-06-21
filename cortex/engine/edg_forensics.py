import logging

try:
    import cortex_core_rs
except ImportError:
    cortex_core_rs = None

logger = logging.getLogger(__name__)

class EDGForensicsOrchestrator:
    """
    CORTEX-PERSIST: Epistemic Dependency Graph Forensics
    Executes Vector 3 (ΔEDG Reconstruction).
    """
    def __init__(self, target_repo: str):
        self.target_repo = target_repo
        if cortex_core_rs:
            self.reconstructor = cortex_core_rs.EDGReconstructor()
            self.delta_engine = cortex_core_rs.DeltaEngine()
        else:
            self.reconstructor = None
            self.delta_engine = None

    def execute_forensics(self, num_commits: int = 10):
        if not self.reconstructor or not self.delta_engine:
            raise RuntimeError("EDG Forensics requires cortex_core_rs for graph reconstruction.")
        
        logger.info(f"Reconstructing EDG from last {num_commits} commits...")
        
        # Extracción mock para el scaffold (en producción usa subprocess con git log)
        commits = self._extract_git_history(num_commits)
        
        previous_hash = None
        previous_ast = None
        
        for commit in commits:
            commit_hash = commit["hash"]
            ast_payload = commit["ast"]
            
            self.reconstructor.add_epistemic_node(commit_hash)
            
            if previous_hash and previous_ast:
                delta = self.delta_engine.compute_delta(previous_ast, ast_payload)
                self.reconstructor.add_causal_transition(previous_hash, commit_hash, delta)
                logger.info(f"Transition: {previous_hash[:8]} -> {commit_hash[:8]} [Δ={delta:.2f}]")
                
                # Check for orphans
                if self.reconstructor.is_orphan(commit_hash):
                    logger.warning(f"Orphan node detected: {commit_hash}. Triggering Apoptosis.")
                
            previous_hash = commit_hash
            previous_ast = ast_payload
            
        logger.info(f"EDG Reconstruction complete. Total Nodes in memory: {self.reconstructor.node_count()}")

    def _extract_git_history(self, num_commits: int):
        """Simula la ingesta de ASTs históricos."""
        return [
            {"hash": f"{i}a{i}b{i}c{i}d{i}e{i}f{i}g", "ast": f"def func(): return {i}"}
            for i in range(num_commits)
        ]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    orchestrator = EDGForensicsOrchestrator(".")
    orchestrator.execute_forensics()
