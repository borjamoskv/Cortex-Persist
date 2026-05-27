import asyncio
import threading

class SyncMixin:
    def _run_sync(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            raise RuntimeError("Cannot call _run_sync from a running event loop")
        return asyncio.run(coro)

    # the rest of the methods
