import asyncio

import pytest

from cortex.engine.ghost_mixin import GhostMixin


class MockEngine(GhostMixin):
    def __init__(self):
        super().__init__()

@pytest.mark.asyncio
async def test_ghost_mixin_songlines():
    engine = MockEngine()
    project = "test_project"
    reference = "EntityX"
    context = "Need to define schema"
    
    # 1. Register
    ghost_id = await engine.register_ghost(reference, context, project)
    assert isinstance(ghost_id, str)
    assert len(ghost_id) == 16
    
    # 2. List
    active = await engine.list_active_ghosts()
    found = any(g['id'] == ghost_id for g in active)
    assert found
    
    # 3. Resolve
    resolved = await engine.resolve_ghost(ghost_id)
    assert resolved
    
    # 4. Verify gone
    active_after = await engine.list_active_ghosts()
    found_after = any(g['id'] == ghost_id for g in active_after)
    assert not found_after
    
    print(f"GhostMixin Songlines Integration Verified. ID: {ghost_id}")

if __name__ == "__main__":
    asyncio.run(test_ghost_mixin_songlines())
