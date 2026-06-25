#!/usr/bin/env python3
"""
[C5-REAL] Sanedrín Daemon Verification Script
Autonomous validation suite for BFT consensus audit and ledger integrity.
Created by Borja Moskv (borjamoskv).
"""
import asyncio
import os
import sys
import subprocess
import shutil

# Add current directory to path to allow importing cortex modules
sys.path.insert(0, os.path.abspath('.'))

from cortex.storage.ledger import EnterpriseAuditLedger

# Define paths for test logs
VALID_LOG_PATH = "test_ledger_valid.jsonl"
CORRUPT_LOG_PATH = "test_ledger_corrupt.jsonl"

async def generate_valid_ledger(path: str):
    """Generates a valid 3-entry WORM ledger using EnterpriseAuditLedger."""
    if os.path.exists(path):
        os.remove(path)
        
    logger_instance = EnterpriseAuditLedger(path)
    
    # Write 3 valid entries
    logger_instance.batch_window_ms = 10 # fast flush
    
    await logger_instance.log_action(
        tenant_id="moskv_c5",
        actor_role="Persist-Executor",
        actor_id="agent_apex",
        action="MUTATION",
        resource="belief_engine",
        status="SUCCESS",
        state_diff="Initial state setup for BFT test"
    )
    
    await logger_instance.log_action(
        tenant_id="moskv_c5",
        actor_role="Persist-Executor",
        actor_id="agent_apex",
        action="UPDATE",
        resource="belief_engine",
        status="SUCCESS",
        state_diff="Updated cognitive vector alignment"
    )
    
    await logger_instance.log_action(
        tenant_id="moskv_c5",
        actor_role="Persist-Executor",
        actor_id="agent_apex",
        action="COMMIT",
        resource="belief_engine",
        status="SUCCESS",
        state_diff="Finalized epoch transition state"
    )
    
    # Wait for the background batch worker to flush queue
    while len(logger_instance._batch_queue) > 0 or logger_instance._batch_task is not None:
        await asyncio.sleep(0.05)
        
    print(f" -> Valid 3-entry ledger generated successfully at {path}")

def corrupt_ledger(src_path: str, dst_path: str):
    """Copies a ledger and corrupts one of the event entries to break the hash chain."""
    if os.path.exists(dst_path):
        os.remove(dst_path)
        
    shutil.copy(src_path, dst_path)
    
    # Read the file lines, modify one, and write back
    with open(dst_path, "r") as f:
        lines = f.readlines()
        
    if not lines:
        raise ValueError("Cannot corrupt an empty ledger file")
        
    # Corrupt the payload of the first entry (usually line 1)
    import json
    data = json.loads(lines[0])
    if "payload" in data:
        data["payload"]["state_diff"] = "CORRUPTED DATA BYZANTINE ATTACK"
    else:
        data["event_hash"] = "0000000000000000000000000000000000000000000000000000000000000000"
        
    lines[0] = json.dumps(data) + "\n"
    
    with open(dst_path, "w") as f:
        f.writelines(lines)
        
    print(f" -> Corrupted ledger generated successfully at {dst_path}")

def run_daemon(ledger_path: str, clear_keys: bool = False) -> subprocess.CompletedProcess:
    """Runs scripts/sanedrin_audit.py as a subprocess with custom environment."""
    env = os.environ.copy()
    env["CORTEX_LEDGER_PATH"] = ledger_path
    
    if clear_keys:
        for k in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY"]:
            env.pop(k, None)
            
    # Run under python interpreter in current virtual environment
    python_bin = sys.executable or "python3"
    
    return subprocess.run(
        [python_bin, "scripts/sanedrin_audit.py"],
        env=env,
        capture_output=True,
        text=True
    )

async def main():
    print("=== STARTING SANEDRÍN DAEMON VERIFICATION SUITE (C5-REAL) ===")
    print("Created by Borja Moskv (borjamoskv)")
    
    # Step 1: Generate valid 3-entry ledger
    await generate_valid_ledger(VALID_LOG_PATH)
    
    # Step 2: Generate corrupted ledger
    corrupt_ledger(VALID_LOG_PATH, CORRUPT_LOG_PATH)
    
    tests_failed = 0
    
    # Test A: Simulates a corrupt ledger entry and verifies the daemon halts execution and logs a P0 alert.
    print("\n--- Test A: Corrupt Ledger Entry and Halting ---")
    proc_a = run_daemon(CORRUPT_LOG_PATH, clear_keys=True)
    print(f"Exit code: {proc_a.returncode}")
    print(f"Stdout:\n{proc_a.stdout.strip()}")
    print(f"Stderr:\n{proc_a.stderr.strip()}")
    
    # Verify non-zero exit code and presence of P0 alert
    if proc_a.returncode != 0 and "[P0]" in proc_a.stderr:
        print("✅ Test A PASSED: Daemon halted with non-zero exit code and emitted [P0] alert.")
    else:
        print("❌ Test A FAILED: Daemon did not halt or did not log [P0] alert.")
        tests_failed += 1
        
    # Test C: Runs the daemon on a valid 3-entry ledger and verifies it completes the audit successfully.
    print("\n--- Test C: Valid 3-Entry Ledger Audit ---")
    proc_c = run_daemon(VALID_LOG_PATH, clear_keys=True) 
    print(f"Exit code: {proc_c.returncode}")
    print(f"Stdout:\n{proc_c.stdout.strip()}")
    print(f"Stderr:\n{proc_c.stderr.strip()}")
    
    if proc_c.returncode == 0 and "Consenso Exitoso" in proc_c.stderr:
        print("✅ Test C PASSED: Daemon successfully completed the audit on valid ledger.")
    else:
        print("❌ Test C FAILED: Daemon failed the audit on a valid ledger.")
        tests_failed += 1
        
    # Cleanup temporary test ledgers
    for path in [VALID_LOG_PATH, CORRUPT_LOG_PATH]:
        if os.path.exists(path):
            os.remove(path)
            
    print("\n================ VERIFICATION SUMMARY ================")
    if tests_failed == 0:
        print("ALL TESTS PASSED SUCCESSFULLY! (C5-REAL)")
        sys.exit(0)
    else:
        print(f"SOME TESTS FAILED: {tests_failed} failure(s) detected.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
