"""CORTEX Knowledge Watcher — VSA Sync Daemon.

Continuously monitors the knowledge directory for any changes and automatically 
compiles semantic vectors into the Persistent ChromaDB instance.
"""

import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import chromadb
except ImportError:
    chromadb = None

logger = logging.getLogger("cortex.mcp.knowledge_watcher")

KNOWLEDGE_DIR = os.path.expanduser("~/.gemini/antigravity/knowledge")
CHROMA_DB_PATH = os.path.expanduser("~/.cortex/chroma_db")

class KnowledgeItemHandler(FileSystemEventHandler):
    def __init__(self, client, collection):
        self.client = client
        self.collection = collection

    def _sync_file(self, file_path: str) -> None:
        if not file_path.endswith("overview.md"):
            return
            
        folder_name = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if content.strip():
                reduced_content = content[:8000]
                self.collection.upsert(
                    documents=[reduced_content],
                    metadatas=[{"source": folder_name}],
                    ids=[folder_name]
                )
                logger.info("👁️ [V3 SINGULARITY] Synced Tensor for KI [%s]", folder_name)
        except Exception as e:
            logger.error("Failed to sync KI %s: %s", folder_name, e)

    def on_modified(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)
            
    def on_created(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)

def start_knowledge_daemon():
    """Starts the background watchdog daemon to keep ChromaDB synced with MD files."""
    if not chromadb or not os.path.exists(KNOWLEDGE_DIR):
        logger.warning("Skipping V3 Knowledge Daemon... (ChromaDB or KNOWLEDGE_DIR missing)")
        return None
        
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(
            "cortex_knowledge_base", 
            metadata={"hnsw:space": "cosine"}
        )
        
        event_handler = KnowledgeItemHandler(client, collection)
        observer = Observer()
        observer.schedule(event_handler, KNOWLEDGE_DIR, recursive=True)
        observer.start()
        
        logger.info("🚀 [V3 KNOWLEDGE WATCHER] Active on %s", KNOWLEDGE_DIR)
        return observer
    except Exception as e:
        logger.error("Cannot start Knowledge Watcher: %s", e)
        return None
