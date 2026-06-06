import asyncio

from cortex.engine.saga_protocol import SagaContext, build_core_write_path_saga


async def test_saga():
    saga = build_core_write_path_saga()
    ctx: SagaContext = {"agent_id": "test_agent", "payload": {"data": "test"}}

    print("Executing SAGA (Success Path)...")
    await saga.execute_mutation(ctx)
    print(f"Resulting context: {ctx}")

    print("\nExecuting SAGA (Failure Path)...")
    # Induce a failure by removing payload before executing
    ctx_fail: SagaContext = {"agent_id": "test_agent"}
    try:
        await saga.execute_mutation(ctx_fail)
    except RuntimeError as e:
        print(f"Caught expected rollback error: {e}")


if __name__ == "__main__":
    asyncio.run(test_saga())
