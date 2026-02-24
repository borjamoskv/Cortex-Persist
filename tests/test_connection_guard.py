"""Tests for ConnectionGuard — CI/lint scanner for raw sqlite3.connect().

Verifies that the scanner correctly detects unauthorized usage
and whitelists legitimate modules.
"""

from pathlib import Path

from cortex.database.connection_guard import scan_raw_connects


class TestConnectionGuardScanner:
    """Test the build-time connection guard scanner."""

    def test_detects_raw_connect(self, tmp_path: Path):
        """Files using sqlite3.connect() directly should be flagged."""
        bad_file = tmp_path / "bad_module.py"
        bad_file.write_text(
            'import sqlite3\nconn = sqlite3.connect("test.db")\n',
            encoding="utf-8",
        )
        violations = scan_raw_connects(tmp_path)
        assert len(violations) == 1
        assert "sqlite3.connect" in violations[0].line_content

    def test_ignores_whitelisted_files(self, tmp_path: Path):
        """Whitelisted files should not trigger violations."""
        # Create a file matching the whitelist pattern
        ok_file = tmp_path / "core.py"
        ok_file.write_text(
            'import sqlite3\nconn = sqlite3.connect("ok.db")\n',
            encoding="utf-8",
        )
        # Whitelist this specific file
        whitelist = frozenset({"core.py"})
        violations = scan_raw_connects(tmp_path, whitelist=whitelist)
        assert len(violations) == 0

    def test_ignores_comments(self, tmp_path: Path):
        """Comments containing sqlite3.connect should not trigger."""
        file = tmp_path / "commented.py"
        file.write_text(
            '# sqlite3.connect("test.db") — this is just a comment\n',
            encoding="utf-8",
        )
        violations = scan_raw_connects(tmp_path)
        assert len(violations) == 0

    def test_clean_files_pass(self, tmp_path: Path):
        """Files without sqlite3.connect() should pass."""
        clean = tmp_path / "clean.py"
        clean.write_text(
            "from cortex.engine import CortexEngine\n"
            "engine = CortexEngine()\n",
            encoding="utf-8",
        )
        violations = scan_raw_connects(tmp_path)
        assert len(violations) == 0

    def test_multiple_violations_detected(self, tmp_path: Path):
        """Multiple files with violations should all be detected."""
        for i in range(3):
            f = tmp_path / f"module_{i}.py"
            f.write_text(
                f'import sqlite3\nconn = sqlite3.connect("db{i}.sqlite")\n',
                encoding="utf-8",
            )
        violations = scan_raw_connects(tmp_path)
        assert len(violations) == 3

    def test_violation_has_line_info(self, tmp_path: Path):
        """Violations should include file path and line number."""
        f = tmp_path / "with_line.py"
        f.write_text(
            "import sqlite3\n\nsome_code = True\n"
            'conn = sqlite3.connect("test.db")\n',
            encoding="utf-8",
        )
        violations = scan_raw_connects(tmp_path)
        assert len(violations) == 1
        assert violations[0].line_number == 4
        assert "with_line.py" in violations[0].filepath


class TestConnectionGuardOnCortex:
    """Integration: scan the actual CORTEX codebase."""

    def test_no_unauthorized_connects_in_cortex(self):
        """The real CORTEX source should pass the connection guard."""
        cortex_root = Path(__file__).parent.parent / "cortex"
        if not cortex_root.exists():
            return  # Skip if not in repo context

        violations = scan_raw_connects(cortex_root)
        # Allow printing for debug even if we don't hard-fail
        for v in violations:
            print(f"  ⚠️  {v}")
        # We assert 0 violations — this is the whole point of the guard
        assert len(violations) == 0, (
            f"Found {len(violations)} unauthorized sqlite3.connect() usage(s). "
            "Use CortexEngine.get_conn() or add to whitelist."
        )
