from babylon60.storage.wal import WriteAheadLog


class SafeEventBatcher:
    async def ingest_event(self, event: dict):
        pass

class BootstrapWatchdog:
    def __init__(self):
        self.wal = WriteAheadLog()
        self.batcher = SafeEventBatcher()
    
    async def recover_and_resume(self):
        """
        Arranque seguro: recuperar eventos no sellados del WAL
        y re-inyectar en el batcher.
        """
        pending = await self.wal.recover_unsealed()
        for event in pending:
            await self.batcher.ingest_event(event)
        return pending
