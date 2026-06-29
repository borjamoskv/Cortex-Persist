"""
NOUS Mutation Ledger.
Sells the state mutation cryptographically.
Reality Level: C5-REAL
"""

from babylon60.crypto.hash_registry import cortex_hash
import json
import time

from pydantic import BaseModel


class LedgerEntry(BaseModel):
    index: int
    timestamp: float
    previous_hash: str
    intent_description: str
    applied_ast: list[dict]
    current_hash: str = ""

    def calculate_hash(self) -> str:
        record = f"{self.index}{self.timestamp}{self.previous_hash}{self.intent_description}{json.dumps(self.applied_ast, sort_keys=True)}"
        return cortex_hash(record.encode("utf-8"))


class MutationLedger:
    """
    An append-only causal chain of state mutations.
    """

    def __init__(self):
        self.chain: list[LedgerEntry] = []
        # Create genesis block
        self._add_entry("GENESIS", [])

    def _add_entry(self, intent_desc: str, ast: list[dict]) -> LedgerEntry:
        prev_hash = self.chain[-1].current_hash if self.chain else "0"
        entry = LedgerEntry(
            index=len(self.chain),
            timestamp=time.time(),
            previous_hash=prev_hash,
            intent_description=intent_desc,
            applied_ast=ast,
        )
        entry.current_hash = entry.calculate_hash()
        self.chain.append(entry)
        return entry

    def record_mutation(self, intent_desc: str, ast: list[dict]) -> str:
        """
        Records the executed AST and returns the new state hash.
        """
        entry = self._add_entry(intent_desc, ast)
        return entry.current_hash

    def verify_chain(self) -> bool:
        """
        Cryptographic verification of the ledger's integrity.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.previous_hash != previous.current_hash:
                return False
            if current.current_hash != current.calculate_hash():
                return False
        return True
