import asyncio
from pathlib import Path

import cortex.routes.admin as admin_routes
import cortex.routes.notebooklm as notebooklm_routes


class _DummyRequest:
    headers = {"Accept-Language": "en"}


class _DummyEngine:
    def search(self, **kwargs):
        return [{"id": "fact-1"}]


def test_export_project_writes_artifact_atomically(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admin_routes, "export_facts", lambda facts, fmt="json": '{"facts":1}\n')

    response = asyncio.run(
        admin_routes.export_project(
            project="demo",
            request=_DummyRequest(),
            path=str(tmp_path / "exports" / "demo.json"),
            fmt="json",
            auth=None,  # type: ignore[arg-type]
            engine=_DummyEngine(),  # type: ignore[arg-type]
        )
    )

    out_path = Path(response.artifact)
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == '{"facts":1}\n'


def test_notebooklm_digest_writes_output_atomically(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    class _DummyService:
        def __init__(self, db_path: str) -> None:
            self.db_path = db_path

        async def generate_digest(self, project=None) -> str:
            return "∆_CTX: one\n∆_CTX: two\n"

    import cortex.services.notebooklm as notebooklm_service

    monkeypatch.setattr(notebooklm_service, "NotebookLMService", _DummyService)

    response = asyncio.run(
        notebooklm_routes.notebooklm_digest(
            project="demo",
            output="exports/digest.md",
            auth=None,  # type: ignore[arg-type]
        )
    )

    out_path = tmp_path / "exports" / "digest.md"
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == "∆_CTX: one\n∆_CTX: two\n"
    assert response["facts_count"] == 2
