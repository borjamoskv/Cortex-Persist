# [C5-REAL] Exergy-Maximized
"""CORTEX Knowledge Watcher - VSA Sync Daemon.

Continuously monitors the knowledge directory for any changes and automatically
compiles semantic vectors into the Persistent SQLite-Vec instance.
"""

import asyncio
import logging
import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import CortexFactModel
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

logger = logging.getLogger("cortex.mcp_server.knowledge_watcher")

KNOWLEDGE_DIR = os.path.expanduser("~/.gemini/antigravity/knowledge")


class KnowledgeItemHandler(FileSystemEventHandler):
    """Handles filesystem events for Knowledge Items."""

    def __init__(self, store: SovereignVectorStoreL2, encoder: AsyncEncoder):
        self.store = store
        self.encoder = encoder

    def _sync_file(self, file_path: str) -> None:
        """Syncs an individual file to SQLite-Vec."""
        if not file_path.endswith("overview.md"):
            return

        # Extract KI folder name
        try:
            parts = file_path.split(os.sep)
            # Expected: .../knowledge/<KI_NAME>/artifacts/overview.md
            ki_name = parts[-3]
        except IndexError:
            ki_name = "unknown_ki"

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if content.strip():
                # Store up to 8k tokens for semantic grounding
                reduced_content = content[:8000]

                async def _async_save():
                    # Generate embedding
                    embedding = await self.encoder.encode(reduced_content)
                    fact = CortexFactModel(
                        id=f"ki_{ki_name}",
                        tenant_id="default",
                        project_id="knowledge",
                        content=reduced_content,
                        embedding=embedding,
                        timestamp=time.time(),
                        is_diamond=True,
                        is_bridge=False,
                        confidence="high",
                        cognitive_layer="semantic",
                        parent_decision_id=None,
                        metadata={"source": ki_name},
                    )
                    await self.store.memorize(fact)

                # Execute async save safely from OS thread
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_async_save())
                except RuntimeError:
                    # No running event loop in this thread (expected for watchdog thread)
                    asyncio.run(_async_save())

                logger.info("👁️ [KNOWLEDGE] Synced Tensor for KI [%s] into SQLite-Vec", ki_name)
        except Exception as e:
            logger.error("Failed to sync KI %s: %s", ki_name, e)

    def on_modified(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)  # type: ignore

    def on_created(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)  # type: ignore


def start_knowledge_daemon():
    """Starts background watchdog daemon to keep SQLite-Vec synced."""
    if not os.path.exists(KNOWLEDGE_DIR):
        msg = "Skipping Knowledge Watcher (KNOWLEDGE_DIR missing)"
        logger.warning(msg)
        return None

    try:
        # Initialize the encoder and store
        encoder = AsyncEncoder()
        store = SovereignVectorStoreL2(encoder=encoder)

        event_handler = KnowledgeItemHandler(store, encoder)
        observer = Observer()
        observer.schedule(event_handler, KNOWLEDGE_DIR, recursive=True)
        observer.start()

        logger.info("🚀 [KNOWLEDGE WATCHER] Active on %s", KNOWLEDGE_DIR)
        return observer
    except Exception as e:
        logger.error("Cannot start Knowledge Watcher: %s", e)
        return None
