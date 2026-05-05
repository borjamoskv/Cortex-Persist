"""CORTEX Knowledge Watcher — VSA Sync Daemon.

Continuously monitors the knowledge directory for any changes and automatically
compiles semantic vectors into the Persistent ChromaDB instance.
"""

import logging
import os

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

try:
    import chromadb
except ImportError:
    chromadb = None

logger = logging.getLogger("cortex.mcp.knowledge_watcher")

KNOWLEDGE_DIR = os.path.expanduser("~/.gemini/antigravity/knowledge")
CHROMA_DB_PATH = os.path.expanduser("~/.cortex/chroma_db")


class KnowledgeItemHandler(FileSystemEventHandler):
    """Handles filesystem events for Knowledge Items."""

    def __init__(self, client, collection):
        self.client = client
        self.collection = collection

    def _sync_file(self, file_path: str) -> None:
        """Syncs an individual file to ChromaDB."""
        if not file_path.endswith("overview.md"):
            return

        # Extract KI folder name
        try:
            parts = file_path.split(os.sep)
            # Expected: .../knowledge/<KI_NAME>/artifacts/overview.md
            # So index of <KI_NAME> is -3
            ki_name = parts[-3]
        except IndexError:
            ki_name = "unknown_ki"

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if content.strip():
                # Store up to 8k tokens for semantic grounding
                reduced_content = content[:8000]
                self.collection.upsert(
                    documents=[reduced_content], metadatas=[{"source": ki_name}], ids=[ki_name]
                )
                logger.info("👁️ [KNOWLEDGE] Synced Tensor for KI [%s]", ki_name)
        except Exception as e:
            logger.error("Failed to sync KI %s: %s", ki_name, e)

    def on_modified(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)


def start_knowledge_daemon():
    """Starts background watchdog daemon to keep ChromaDB synced."""
    if not chromadb or not os.path.exists(KNOWLEDGE_DIR):
        msg = "Skipping Knowledge Watcher (ChromaDB or KNOWLEDGE_DIR missing)"
        logger.warning(msg)
        return None

    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(
            "cortex_knowledge_base", metadata={"hnsw:space": "cosine"}
        )

        event_handler = KnowledgeItemHandler(client, collection)
        observer = Observer()
        observer.schedule(event_handler, KNOWLEDGE_DIR, recursive=True)
        observer.start()

        logger.info("🚀 [KNOWLEDGE WATCHER] Active on %s", KNOWLEDGE_DIR)
        return observer
    except Exception as e:
        logger.error("Cannot start Knowledge Watcher: %s", e)
        return None
