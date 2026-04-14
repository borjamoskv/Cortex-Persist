from pathlib import Path

from cortex.utils.syscall import SovereignSys


def test_sovereign_sys_write_persists_file_atomically(tmp_path: Path) -> None:
    sysif = SovereignSys(tmp_path)

    result = sysif.write("nested/output.txt", "hello cortex")

    assert result == "[SUCCESS] Wrote to nested/output.txt"
    assert (tmp_path / "nested" / "output.txt").read_text(encoding="utf-8") == "hello cortex"


def test_sovereign_sys_write_rejects_paths_outside_root(tmp_path: Path) -> None:
    sysif = SovereignSys(tmp_path)

    result = sysif.write("../escape.txt", "blocked")

    assert result == "[ERROR] Access denied: ../escape.txt is outside sandbox."
