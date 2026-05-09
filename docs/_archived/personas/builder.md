# Hello World in 3 Minutes

As an engineer or builder integrating CORTEX Persist, your goal is to seamlessly plug cryptographic memory into your existing agent loops without rewriting your architecture.

CORTEX is local-first, async-native, and drop-in ready.

## 1. Install & Init

```bash
# Install the core Engine (SQLite + Vector Search bindings included)
pip install cortex-persist

# Initialize the cryptographic ledger in your current directory
cortex init
```

## 2. Store a Fact from your Agent

Whenever your agent makes a rigid decision, writes a tool output, or commits to a state, intercept that event and dump it into CORTEX.

```python
import asyncio
from cortex import CortexEngine

async def agent_loop():
    # Automatically binds to the local ./cortex.db ledger
    engine = CortexEngine()
    
    # 1. Your LLM decides to delete a user's file.
    # 2. You store that decision cryptographically.
    fact_id = await engine.store(
        project="desktop-cleaner-bot",
        content="Action executed: Deleted system32 due to suspected malware.",
        fact_type="irreversible_action",
    )
    
    print(f"Persisted as fact #{fact_id}")

asyncio.run(agent_loop())
```

## 3. Verify Your Logic

If your agent goes rogue, or a user complains that a file was mysteriously deleted, you don't grep through unstructured logs. You verify the chain.

```bash
# Returns VERIFIED if the row was untouched, or TAMPERED if the DB was altered.
cortex trust-ledger verify
```

## Next Steps for Builders:
- [Read the SDK Surface](../SDK-SURFACE.md)
- [Review the Event Model](../EVENT-MODEL.md)
- [Understand the API Classes](../reference.md)
