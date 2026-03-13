# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import asyncio
import logging
import os
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger("cortex.daemon.loops.watcher")


class GitWatcherHandler(FileSystemEventHandler):
    def __init__(self, state, cortex_root, osc_client, speak_func, evolution_func, loop):
        self.state = state
        self.cortex_root = cortex_root
        self.osc_client = osc_client
        self.speak_func = speak_func
        self.evolution_func = evolution_func
        self.loop = loop

    def on_modified(self, event):
        if "HEAD" in event.src_path:
            self.state.daemons["git_watcher"]["last_event"] = time.strftime("%H:%M:%S")
            self.osc_client.send_message("/cortex/git_pulse", 1.0)

            async def check_ghosts():
                try:
                    from cortex.engine import CortexEngine

                    engine = CortexEngine()
                    modified_path = Path(event.src_path)
                    if modified_path.name == "HEAD":
                        ghosts = await engine.list_active_ghosts(root_dir=self.cortex_root)
                    else:
                        ghosts = await engine.list_active_ghosts(root_dir=modified_path.parent)

                    if ghosts:
                        count = 0
                        for g in ghosts:
                            if str(modified_path) in g["source_file"]:
                                count += 1
                        if count > 0:
                            await self.speak_func(
                                self.state,
                                f"Atención: {count} ghosts detectados en zona de mutación.",
                            )
                except (ImportError, OSError, ValueError) as exc:
                    logger.debug(
                        "Ghost check skipped: %s",
                        exc,
                    )

            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.speak_func(self.state, "Mutación detectada."), self.loop
                )
                asyncio.run_coroutine_threadsafe(check_ghosts(), self.loop)
                # Note: evolution_loop is usually a long-running loop, not a one-off.
                # In the original code it was started on every mutation.
                asyncio.run_coroutine_threadsafe(
                    self.evolution_func(self.state, self.cortex_root, self.speak_func), self.loop
                )


async def git_watcher_loop(state, cortex_root, osc_client, speak_func, evolution_func, loop):
    state.daemons["git_watcher"]["status"] = "online"
    path_to_watch = str(cortex_root / ".git")
    if not os.path.exists(path_to_watch):
        state.daemons["git_watcher"]["status"] = "error: .git not found"
        return

    event_handler = GitWatcherHandler(
        state, cortex_root, osc_client, speak_func, evolution_func, loop
    )
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=False)
    observer.start()
    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        observer.stop()
        raise
    finally:
        observer.join()
