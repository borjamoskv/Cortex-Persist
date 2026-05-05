from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


def test_get_embedder_uses_runtime_local_embedder(tmp_path: Path) -> None:
    repo_root_path = Path(__file__).resolve().parents[1]
    repo_root = repr(str(repo_root_path))
    db_path = repr(str(tmp_path / "embedder.db"))
    script = textwrap.dedent(
        f"""
        import sys
        from pathlib import Path

        sys.path.insert(0, {repo_root})

        import cortex.embeddings as embeddings_module
        from cortex.engine import CortexEngine

        class DummyEmbedder:
            created = 0

            def __init__(self) -> None:
                DummyEmbedder.created += 1

        embeddings_module.LocalEmbedder = DummyEmbedder

        engine = CortexEngine(db_path=Path({db_path}))
        embedder = engine._get_embedder()

        assert isinstance(embedder, DummyEmbedder)
        assert engine._get_embedder() is embedder
        assert DummyEmbedder.created == 1
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
