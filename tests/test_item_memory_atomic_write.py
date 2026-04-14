import json
from pathlib import Path

from cortex.memory.hdc.item_memory import ItemMemory


def test_item_memory_save_codebook_writes_json_file(tmp_path: Path) -> None:
    codebook_path = tmp_path / "hdc" / "codebook.json"
    memory = ItemMemory(dim=16, codebook_path=codebook_path)

    memory.encode("token:alpha")
    memory.save_codebook()

    assert codebook_path.exists()
    data = json.loads(codebook_path.read_text(encoding="utf-8"))
    assert data["dim"] == 16
    assert "token:alpha" in data["vectors"]
