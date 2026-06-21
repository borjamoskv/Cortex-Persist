"""
NOUS Intent Architecture - End to End C5-REAL Demo.
"""

from cortex.nous.dry_run import DryRunSimulator
from cortex.nous.judge import DeterministicJudge
from cortex.nous.ledger import MutationLedger
from cortex.nous.parser import IntentParser


def run_demo():
    print("=== [NOUS] INITIALIZING C5-REAL KERNEL ===")

    # 1. Stochastic Intent (Simulated LLM output)
    print("\n[1] STOCHASTIC INTENT RECEIVED")
    raw_llm_output = """
    {
        "description": "Create a users table and add a generic metadata column",
        "actions": [
            {
                "action_type": "CREATE_TABLE",
                "table_name": "users",
                "parameters": {
                    "id": "INTEGER PRIMARY KEY",
                    "username": "TEXT NOT NULL"
                }
            },
            {
                "action_type": "ADD_COLUMN",
                "table_name": "users",
                "parameters": {
                    "name": "metadata",
                    "type": "JSON"
                }
            }
        ]
    }
    """

    try:
        # Phase 1: Parse
        intent = IntentParser.parse_llm_json(raw_llm_output)
        print(f" -> Parsed AST: {len(intent.actions)} actions derived from '{intent.description}'")

        # Phase 2: Judge
        verdict = DeterministicJudge.evaluate(intent)
        print(
            f"\n[2] DETERMINISTIC JUDGE VERDICT: {'APPROVED' if verdict.approved else 'REJECTED'}"
        )
        if not verdict.approved:
            print(f" -> Reason: {verdict.reason}")
            return
        for w in verdict.warnings:
            print(f" -> Warning: {w}")

        # Phase 3: Dry-Run
        print("\n[3] DRY-RUN SIMULATION")
        is_valid = DryRunSimulator.simulate(intent)
        print(f" -> Simulation {'PASSED' if is_valid else 'FAILED'}")
        if not is_valid:
            return

        # Phase 4: Ledger Crystallization
        print("\n[4] STATE CRYSTALLIZATION (LKRGSER)")
        ledger = MutationLedger()
        ast_dict = [a.model_dump() for a in intent.actions]
        new_hash = ledger.record_mutation(intent.description, ast_dict)

        print(" -> Mutation sealed.")
        print(f" -> New State Hash: {new_hash}")
        print(f" -> Ledger Integrity Valid: {ledger.verify_chain()}")

    except Exception as e:
        print(f"System Error: {e}")


if __name__ == "__main__":
    run_demo()
