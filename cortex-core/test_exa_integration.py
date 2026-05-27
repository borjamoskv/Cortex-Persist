import asyncio
from persistence import enqueue_swarm_task, HybridPersistenceManager

async def main():
    HybridPersistenceManager()
    
    # Inyectar tarea de tipo LISP al Enjambre
    print("[+] Inyectando EXA_LISP payload...")
    payload = {
        "type": "EXA_LISP",
        "code": "(with-exergy-limit 500j (z3-verify (infer qwen_local local_tensor)))",
        "exergy_limit": 500
    }
    
    enqueue_swarm_task("SAGE_COUNCIL", payload)
    
    # Wait for Outbox drainer
    await asyncio.sleep(2)
    print("[+] Test completado. Revisa log output del daemon.")

if __name__ == "__main__":
    asyncio.run(main())
