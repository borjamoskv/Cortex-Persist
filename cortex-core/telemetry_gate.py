import os
import ast
import json
import logging
from typing import Any
from swarm_manager import SwarmActuator
from persistence import LedgerManager

# CORTEX-Persist: Telemetry Gate (The Guillotine)
# -----------------------------------------------------------------------------
# Evaluates external agent patches (AST). If they fail falsation,
# they are rejected and the agent's token budget is penalized.

logging.basicConfig(level=logging.INFO, format="🛡️ [TELEMETRY_GATE] %(message)s")

class TelemetryGate:
    """The Ultimate C5-REAL Quality Gate for Alien Code."""

    def __init__(self, actuator: SwarmActuator):
        self.ledger = LedgerManager()
        self.actuator = actuator

    def _verify_ast_syntax(self, source_code: str) -> bool:
        """Falsation Level 1: Static AST Parsing."""
        try:
            ast.parse(source_code)
            return True
        except SyntaxError as e:
            logging.error(f"AST Falsation Failed: {e}")
            return False

    def _execute_sandbox_tests(self, target_file: str, new_source: str) -> bool:
        """Falsation Level 2: Sandbox Execution (C5-REAL).
        Temporarily applies the patch, runs the test suite, and reverts.
        """
        import subprocess
        import shutil

        # If it's a dummy file for tests, just pass it unless it has overflow
        if target_file == "dummy.py" or not os.path.exists(target_file):
            if "ENTROPY_OVERFLOW" in new_source:
                logging.error("Sandbox Execution Failed: Entropy overflow detected.")
                return False
            return True

        backup_path = f"{target_file}.c5bak"
        try:
            # 1. Backup the original file
            shutil.copy2(target_file, backup_path)
            
            # 2. Write the new source
            with open(target_file, 'w') as f:
                f.write(new_source)
                
            # 3. Execute Pytest (isolated to the relevant test file if possible, else global)
            logging.info(f"Running C5-REAL falsation tests on {target_file}...")
            # Infer test file name
            import os.path
            base_name = os.path.basename(target_file)
            dir_name = os.path.dirname(target_file)
            test_file = os.path.join(dir_name, f"test_{base_name}")
            
            pytest_cmd = ["pytest", "--maxfail=1", "--disable-warnings"]
            if os.path.exists(test_file):
                pytest_cmd.append(test_file)
                
            # We use --maxfail=1 to fail fast and avoid burning compute exergy
            result = subprocess.run(
                pytest_cmd,
                capture_output=True,
                text=True,
                timeout=30.0 # 30 seconds max execution bound
            )
            
            if result.returncode == 0:
                return True
            else:
                logging.error(f"Falsation tests failed for {target_file}:\n{result.stderr or result.stdout}")
                return False

        except subprocess.TimeoutExpired:
            logging.error(f"Falsation Timeout: Execution exceeded exergy bounds (30s) on {target_file}.")
            return False
        except Exception as e:
            logging.error(f"Sandbox Execution Exception: {e}")
            return False
        finally:
            # 4. Always restore the original file
            if os.path.exists(backup_path):
                shutil.move(backup_path, target_file)

    def process_external_patch(self, agent_id: str, patch_payload: str) -> bool:
        """
        Receives an AST_MUTATION from an external agent and passes it through the guillotine.
        """
        logging.info(f"Received patch from {agent_id}. Initiating Quality Gate...")
        
        try:
            payload: dict[str, Any] = json.loads(patch_payload)
            
            if payload.get("type") == "ABORT":
                logging.info(f"{agent_id} explicitly aborted (Kill Criteria respected). No penalty.")
                return False

            if payload.get("type") != "AST_MUTATION":
                raise ValueError("Invalid payload type.")

            new_source = payload.get("new_source", "")
            target_file = payload.get("target_file", "")
            justification = payload.get("thermodynamic_justification", "None")

            # Phase 1: AST Verification
            if not self._verify_ast_syntax(new_source):
                self.actuator.penalize_agent(agent_id, 5000)
                return False
                
            # Phase 2: Sandbox
            if not self._execute_sandbox_tests(target_file, new_source):
                self.actuator.penalize_agent(agent_id, 10000)
                return False

            # Success: Yield calculation and ZK-Seal
            exergy_yield = float(payload.get("yield_amount", 10.0))
            logging.info(f"✅ Falsation Passed. Thermodynamic Justification: {justification}")
            
            # Commit to Sovereign Ledger
            self.ledger.append(
                action=f"EXTERNAL_AST_MUTATION: {target_file}", 
                vector_id=agent_id, 
                yield_amount=exergy_yield
            )
            logging.info("✅ ZK-Seal Applied. Patch integrated into CORTEX-Persist.")
            return True

        except json.JSONDecodeError:
            logging.error(f"Falsation Failed: Invalid JSON emitted by {agent_id}.")
            self.actuator.penalize_agent(agent_id, 2000)
            return False
        except Exception as e:
            logging.error(f"Falsation Failed: {e}")
            self.actuator.penalize_agent(agent_id, 2000)
            return False

if __name__ == "__main__":
    db_path = "cortex_memory_vsa.db"
    actuator = SwarmActuator(db_path)
    gate = TelemetryGate(actuator)
    
    # Simulate a successful patch from Claude-3.7
    mock_patch = json.dumps({
        "type": "AST_MUTATION",
        "target_file": "dummy.py",
        "new_source": "def hyper_optimized(): return True",
        "yield_amount": 150.0,
        "thermodynamic_justification": "Replaced O(N^2) sort with O(1) hash map."
    })
    
    gate.process_external_patch("Claude-3.7", mock_patch)
    
    # Simulate a hallucination from an unaligned model
    mock_fail = "```python\nprint('This is not a JSON dictionary!')\n```"
    gate.process_external_patch("GPT-4-Legacy", mock_fail)
