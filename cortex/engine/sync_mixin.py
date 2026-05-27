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
            raise RuntimeError("Cannot call _run_sync from a running event loop. Use await instead.")
            
        tls = self.__dict__.setdefault("_sync_tls", threading.local())
        if not hasattr(tls, "loop") or tls.loop.is_closed():
            tls.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(tls.loop)
            
        return tls.loop.run_until_complete(coro)

    def init_db_sync(self) -> None:
        return self._run_sync(self.init_db())

    def store_sync(self, *args, **kwargs):
        return self._run_sync(self.store(*args, **kwargs))

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
        """Close the underlying engine and stop the background sync loop."""
        import logging

        logger = logging.getLogger(__name__)

        if hasattr(self, "_sync_loop") and not self._sync_loop.is_closed():
            try:
                self._run_sync(self.close())
            except Exception as e:
                logger.exception(f"[SyncMixin] Error closing async engine synchronously: {e}")

            lock = self.__dict__.setdefault("_instance_sync_lock", threading.Lock())
            with lock:
                if hasattr(self, "_sync_loop"):
                    loop = self._sync_loop
                    
                    async def _cancel_tasks():
                        tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
                        for t in tasks:
                            t.cancel()
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)
                        
                    try:
                        asyncio.run_coroutine_threadsafe(_cancel_tasks(), loop).result(timeout=5.0)
                    except Exception as e:
                        logger.exception(f"[SyncMixin] Error cancelling tasks during shutdown: {e}")
                    
                    loop.call_soon_threadsafe(loop.stop)
                    
                    if hasattr(self, "_sync_thread"):
                        self._sync_thread.join(timeout=2.0)
                        delattr(self, "_sync_thread")
                    
                    if not loop.is_closed():
                        loop.close()
                    delattr(self, "_sync_loop")
        else:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.close())
            except RuntimeError:
                try:
                    asyncio.run(self.close())
                except Exception as e:
                    logger.exception(f"[SyncMixin] Error closing async engine via asyncio.run: {e}")

    def health_check_sync(self, *args, **kwargs):
        return self._run_sync(self.health_check(*args, **kwargs))

    def health_report_sync(self, *args, **kwargs):
        return self._run_sync(self.health_report(*args, **kwargs))

    def fingerprint_sync(self, *args, **kwargs):
        return self._run_sync(self.fingerprint(*args, **kwargs))

    def immortality_index_sync(self, *args, **kwargs):
        return self._run_sync(self.immortality_index(*args, **kwargs))
