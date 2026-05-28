import asyncio

from cortex.engine import CortexEngine
from cortex.extensions.episodic.main import EpisodicMemory


async def seed():
    engine = CortexEngine()
    await engine.init_db()

    async with engine.session() as conn:
        episodic = EpisodicMemory(conn)
        session_id = "mock-session-123"
        project = "cortex-core"

        # 1. Initial intent
        await episodic.record(
            session_id=session_id,
            event_type="decision",
            content="Plan: Fix the Landauer LOC barrier in schema.py",
            project=project,
            meta={"intent": "Fix the Landauer LOC barrier in schema.py"},
        )

        # 2. Action 1
        await episodic.record(
            session_id=session_id,
            event_type="decision",
            content="Calling list_dir",
            project=project,
            meta={
                "tool": "list_dir",
                "input": {"DirectoryPath": "./cortex"},
            },
        )

        # 3. Observation 1
        await episodic.record(
            session_id=session_id,
            event_type="discovery",
            content="Found schema.py and schema_extensions.py",
            project=project,
        )

        # 4. Action 2 (The fix)
        await episodic.record(
            session_id=session_id,
            event_type="decision",
            content="Moving code to extensions",
            project=project,
            meta={
                "tool": "replace_file_content",
                "input": {"TargetFile": "schema.py", "lines": "..."},
            },
        )

        # 5. Observation 2 (Success)
        await episodic.record(
            session_id=session_id,
            event_type="milestone",
            content="Success: LOC barrier respected. Tests passing.",
            project=project,
            meta={"tests_passed": True},
        )

    await engine.close()
    print("Seed data created successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
