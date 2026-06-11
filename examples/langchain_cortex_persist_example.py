"""Example: Cortex-Persist as auditable memory backend for a LangChain chain.

Requires:
    pip install cortex-persist langchain langchain-openai

Set OPENAI_API_KEY before running.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain.chains import LLMChain
from langchain.memory import BaseMemory
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

try:
    from cortex import CortexEngine
except ImportError as exc:
    raise SystemExit(
        "Install Cortex-Persist first:\n"
        "  pip install cortex-persist\n"
        "  # or: pip install git+https://github.com/borjamoskv/Cortex-Persist.git"
    ) from exc


# ---------------------------------------------------------------------------
# Memory wrapper
# ---------------------------------------------------------------------------

class CortexPersistMemory(BaseMemory):
    """LangChain BaseMemory backed by Cortex-Persist.

    Every interaction is appended to the tamper-evident ledger.
    `load_memory_variables` reconstructs the recent history for prompt injection.
    """

    def __init__(self, engine: CortexEngine, limit: int = 10) -> None:
        self.engine = engine
        self.limit = limit
        self._buffer: list[dict] = []

    @property
    def memory_variables(self) -> List[str]:
        return ["history"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        lines: List[str] = []
        for item in self._buffer[-self.limit :]:
            user_text = item.get("inputs", {}).get("input", "")
            ai_text = item.get("outputs", {}).get("output", "")
            if user_text:
                lines.append(f"User: {user_text}")
            if ai_text:
                lines.append(f"Assistant: {ai_text}")
        return {"history": "\n".join(lines)}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        entry = {"inputs": inputs, "outputs": outputs, "source": "langchain-example"}
        self._buffer.append(entry)
        # Seal every interaction into the Cortex-Persist ledger
        self.engine.observe("langchain_input", str(inputs))
        self.engine.observe("langchain_output", str(outputs))

    def clear(self) -> None:
        self._buffer.clear()


# ---------------------------------------------------------------------------
# Chain builder
# ---------------------------------------------------------------------------

def build_chain(engine: CortexEngine) -> LLMChain:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY before running this example.")

    memory = CortexPersistMemory(engine=engine, limit=8)

    prompt = ChatPromptTemplate.from_template(
        """
        You are a technical assistant with tamper-evident memory powered by Cortex-Persist.

        Recent conversation history:
        {history}

        User: {input}
        Assistant:""".strip()
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    return LLMChain(llm=llm, prompt=prompt, memory=memory, verbose=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    engine = CortexEngine()

    chain = build_chain(engine)

    # Turn 1 — store a fact
    r1 = chain.invoke({"input": "My project is called Cortex-Persist. Remember it."})
    print("\n[Turn 1]", r1.get("text", r1))

    # Turn 2 — verify memory
    r2 = chain.invoke({"input": "What is the name of my project?"})
    print("\n[Turn 2]", r2.get("text", r2))

    # Turn 3 — another fact
    r3 = chain.invoke({"input": "The project uses SHA-256 Merkle seals for tamper evidence."})
    print("\n[Turn 3]", r3.get("text", r3))

    # Seal the full session and verify integrity
    proof = engine.seal()
    print("\n--- Cortex-Persist Integrity Proof ---")
    print(f"Hash  : {proof.hash}")
    print(f"Valid : {proof.verify()}")
    print("Session cryptographically sealed. Tamper-evident by construction.")


if __name__ == "__main__":
    main()
