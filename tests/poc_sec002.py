import asyncio
import sqlite3
from cortex.routes.facts import get_causal_chain

print("PoC SEC-002 Generated: Verifying signature of get_causal_chain...")
import inspect
sig = inspect.signature(get_causal_chain)
print("Signature:", sig)
if 'tenant_id' not in sig.parameters:
    print("VULNERABILITY CONFIRMED: tenant_id is missing from route parameters.")
else:
    print("NOT VULNERABLE.")
