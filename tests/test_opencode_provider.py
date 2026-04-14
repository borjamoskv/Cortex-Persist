import asyncio
import inspect

from cortex.extensions.llm.opencode_provider import OpenCodeProvider
import cortex.extensions.llm.opencode_provider as opencode_provider


class _DummyQuotaManager:
    async def acquire(self, tokens: int) -> None:
        return None


def test_run_opencode_uses_exec_and_writes_prompt_to_stdin(monkeypatch) -> None:
    calls: list[tuple[tuple[object, ...], bytes | None]] = []

    class DummyProcess:
        returncode = 0

        async def communicate(self, data: bytes | None = None):
            calls.append((self.args, data))
            return b"ok", b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        proc = DummyProcess()
        proc.args = args
        return proc

    monkeypatch.setattr(opencode_provider, "_get_quota_manager", lambda: _DummyQuotaManager())
    monkeypatch.setattr(
        opencode_provider.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    provider = OpenCodeProvider()
    result = asyncio.run(provider._run_opencode("hola"))

    assert result == "ok"
    assert calls == [
        (
            ("opencode", "run", "-", "--model", "anthropic/claude-sonnet-4-5"),
            b"hola",
        )
    ]


def test_stream_opencode_no_longer_uses_shell() -> None:
    source = inspect.getsource(OpenCodeProvider._stream_opencode)

    assert "create_subprocess_exec" not in source
    assert "_spawn_opencode_process" in source
    assert "create_subprocess_shell" not in source
