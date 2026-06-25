# [C5-REAL] Exergy-Maximized

import asyncio
import logging
from typing import Any

from legacy_research.memory.memory_compression import compress_and_store

logger = logging.getLogger("cortex.memory._manager_bg")


async def compression_worker_loop(worker_id: int, bg_queue: asyncio.Queue, manager: Any) -> None:
    """Persistent worker loop consuming from the background queue."""
    while True:
        try:
            overflowed, session_id, tenant_id, project_id = await bg_queue.get()
            try:
                await compress_and_store(manager, overflowed, session_id, tenant_id, project_id)
            except (ValueError, TypeError, RuntimeError, OSError) as e:
                logger.error("MemoryManager: Worker %d failed compression: %s", worker_id, e)
            finally:
                bg_queue.task_done()
        except asyncio.CancelledError:
            raise
        except (ValueError, TypeError, RuntimeError, OSError) as e:
            logger.error("MemoryManager: Worker %d encountered fatal error: %s", worker_id, e)
            await asyncio.sleep(1)


async def cancel_background_tasks(
    bg_workers: list[asyncio.Task], bg_queue: asyncio.Queue, memory_os: Any, dynamic_space: Any
) -> None:
    """Cancel pending tasks and workers aggressively to prevent event loop leaks."""
    logger.debug("Canceling all background workers and Glial Daemon.")
    tasks_to_wait = []
    if memory_os and getattr(memory_os, "_glial_daemon_task", None):
        memory_os._glial_daemon_task.cancel()
        tasks_to_wait.append(memory_os._glial_daemon_task)

    for worker in bg_workers:
        if not worker.done():
            worker.cancel()
            tasks_to_wait.append(worker)

    if dynamic_space:
        try:
            await dynamic_space.stop()
        except Exception as e:
            logger.error("Error stopping dynamic semantic space: %s", e)

    if tasks_to_wait:
        try:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)
        except Exception as e:
            logger.debug("Failed to gather tasks: %s", e)

    bg_workers.clear()

    # Flush the queue
    while not bg_queue.empty():
        try:
            bg_queue.get_nowait()
            bg_queue.task_done()
        except asyncio.QueueEmpty:
            break
