import asyncio
import threading


# pyright: reportAttributeAccessIssue=false
class SyncMixin:
    def _run_sync(self, coro):
        """Execute a coroutine synchronously, thread-safe on a persistent background loop."""
        if not hasattr(self, "_sync_loop") or self._sync_loop.is_closed():
            import threading

            global_lock = globals().setdefault("_cortex_sync_lock", threading.Lock())
            with global_lock:
                if not hasattr(self, "_sync_loop") or self._sync_loop.is_closed():
                    self._sync_loop = asyncio.new_event_loop()
                    self._sync_thread = threading.Thread(
                        target=self._sync_loop.run_forever, name="CortexSyncLoopThread", daemon=True
                    )
                    self._sync_thread.start()

        future = asyncio.run_coroutine_threadsafe(coro, self._sync_loop)
        try:
            return future.result()
        except Exception as e:
            raise e

    def init_db_sync(self) -> None:
        return self._run_sync(self.init_db())

    def store_sync(self, *args, **kwargs):
        return self._run_sync(self.store(*args, **kwargs))

    def recall_sync(self, *args, **kwargs):
        return self._run_sync(self.recall(*args, **kwargs))

    def search_sync(self, *args, **kwargs):
        return self._run_sync(self.search(*args, **kwargs))

    def hybrid_search_sync(self, *args, **kwargs):
        return self._run_sync(self.search(*args, **kwargs))

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
        """Close the underlying engine and stop the background sync loop."""
        if hasattr(self, "_sync_loop") and not self._sync_loop.is_closed():
            try:
                self._run_sync(self.close())
            except Exception:
                pass
            import threading

            global_lock = globals().setdefault("_cortex_sync_lock", threading.Lock())
            with global_lock:
                if hasattr(self, "_sync_loop"):
                    loop = self._sync_loop
                    loop.call_soon_threadsafe(loop.stop)
                    if hasattr(self, "_sync_thread"):
                        self._sync_thread.join(timeout=2.0)
                        delattr(self, "_sync_thread")
                    delattr(self, "_sync_loop")
        else:
            try:
                asyncio.run(self.close())
            except (RuntimeError, Exception):
                pass

    def health_check_sync(self, *args, **kwargs):
        return self._run_sync(self.health_check(*args, **kwargs))

    def health_report_sync(self, *args, **kwargs):
        return self._run_sync(self.health_report(*args, **kwargs))

    def fingerprint_sync(self, *args, **kwargs):
        return self._run_sync(self.fingerprint(*args, **kwargs))

    def immortality_index_sync(self, *args, **kwargs):
        return self._run_sync(self.immortality_index(*args, **kwargs))
