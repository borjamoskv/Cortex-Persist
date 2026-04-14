import asyncio
import json
import sqlite3
from pathlib import Path

from cortex.extensions.daemon.monitors.security import SecurityMonitor


def test_check_async_keeps_log_when_processing_fails(tmp_path: Path) -> None:
    log_path = tmp_path / "firewall.log"
    log_path.write_text(json.dumps({"payload": "attack", "ip_address": "1.2.3.4"}) + "\n")
    monitor = SecurityMonitor(log_path=str(log_path))

    async def failing_get_store():
        raise sqlite3.OperationalError("db unavailable")

    monitor._get_store = failing_get_store  # type: ignore[method-assign]

    alerts = asyncio.run(monitor.check_async())

    assert alerts == []
    assert log_path.read_text(encoding="utf-8").strip()


def test_check_async_clears_log_after_successful_processing(tmp_path: Path) -> None:
    log_path = tmp_path / "firewall.log"
    log_path.write_text(json.dumps({"payload": "attack", "ip_address": "1.2.3.4"}) + "\n")
    monitor = SecurityMonitor(log_path=str(log_path))

    async def fake_get_store():
        return object()

    async def fake_process_single_event(store, event):
        return None

    monitor._get_store = fake_get_store  # type: ignore[method-assign]
    monitor._process_single_event = fake_process_single_event  # type: ignore[method-assign]

    alerts = asyncio.run(monitor.check_async())

    assert alerts == []
    assert log_path.read_text(encoding="utf-8") == ""
