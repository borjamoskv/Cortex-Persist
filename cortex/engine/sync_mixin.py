# [C5-REAL] Exergy-Maximized
import asyncio
import threading


# pyright: reportAttributeAccessIssue=false
class SyncMixin:
    def _run_sync(self, coro):
        """Execute a coroutine synchronously, avoiding the single-thread I/O bottleneck."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            raise RuntimeError(
                "Cannot call _run_sync from a running event loop. Use await instead."
            )

        tls = self.__dict__.setdefault("_sync_tls", threading.local())
        if not hasattr(tls, "loop") or tls.loop.is_closed():
            tls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(tls.loop)

        return tls.loop.run_until_complete(coro)

    def init_db_sync(self) -> None:
        return self._run_sync(self.init_db())

    def store_sync(self, *args, **kwargs):
        return self._run_sync(self.store(*args, **kwargs))

    def store_many_sync(self, *args, **kwargs):
        return self._run_sync(self.store_many(*args, **kwargs))

    def recall_sync(self, *args, **kwargs):
        return self._run_sync(self.recall(*args, **kwargs))

    def search_sync(self, *args, **kwargs):
        return self._run_sync(self.search(*args, **kwargs))

    def hybrid_search_sync(self, *args, **kwargs):
        return self._run_sync(self.hybrid_search(*args, **kwargs))

    def recall_episode_sync(self, *args, **kwargs):
        return self._run_sync(self.recall_episode(*args, **kwargs))

    def trace_episode_sync(self, *args, **kwargs):
        return self._run_sync(self.trace_episode(*args, **kwargs))

    def graph_sync(self, *args, **kwargs):
        return self._run_sync(self.graph(*args, **kwargs))

    def query_entity_sync(self, *args, **kwargs):
        return self._run_sync(self.query_entity(*args, **kwargs))

    def get_causal_chain_sync(self, *args, **kwargs):
        return self._run_sync(self.get_causal_chain(*args, **kwargs))

    def close_sync(self):
        """Close the underlying engine and clean up the thread-local event loop."""
        import logging

        logger = logging.getLogger(__name__)

        self._closing = True  # Guard to prevent new checkpointing and tasks
        try:
            self._run_sync(self.close())
        except (RuntimeError, asyncio.TimeoutError) as e:
            logger.exception(f"[SyncMixin] Error closing async engine synchronously: {e}")

        tls = self.__dict__.get("_sync_tls")
        if tls and hasattr(tls, "loop"):
            loop = tls.loop
            if not loop.is_closed():
                try:
                    tasks = asyncio.all_tasks(loop)
                    for t in tasks:
                        t.cancel()
                    if tasks:
                        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

                    if hasattr(loop, "shutdown_asyncgens"):
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    if hasattr(loop, "shutdown_default_executor"):
                        try:
                            loop.run_until_complete(loop.shutdown_default_executor())
                        except NotImplementedError:
                            import logging

                            pass

                    loop.close()
                except (RuntimeError, ValueError) as e:
                    logger.debug(f"[SyncMixin] Handled error during loop teardown: {e}")
            delattr(tls, "loop")

    def health_check_sync(self, *args, **kwargs):
        return self._run_sync(self.health_check(*args, **kwargs))

    def health_report_sync(self, *args, **kwargs):
        return self._run_sync(self.health_report(*args, **kwargs))

    def fingerprint_sync(self, *args, **kwargs):
        return self._run_sync(self.fingerprint(*args, **kwargs))

    def immortality_index_sync(self, *args, **kwargs):
        return self._run_sync(self.immortality_index(*args, **kwargs))
