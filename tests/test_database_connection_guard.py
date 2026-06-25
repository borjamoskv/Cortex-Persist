# [C5-REAL] Exergy-Maximized
"""Tests for babylon60.database.connection_guard - CI/lint scanner for raw sqlite3 usage.

C5-REAL audit remediation: database/ coverage gap.
"""

import textwrap
from pathlib import Path

import pytest

from babylon60.database.connection_guard import (
    ConnectionViolation,
    _scan_file_lines,
    scan_raw_connects,
)


# ── ConnectionViolation ──────────────────────────────────────────────────


class TestConnectionViolation:
    def test_str_format(self):
        v = ConnectionViolation("cortex/foo.py", 42, "  conn = sqlite3.connect(db)  ")
        assert str(v) == "cortex/foo.py:42: conn = sqlite3.connect(db)"

    def test_repr(self):
        v = ConnectionViolation("cortex/foo.py", 42, "line")
        assert "ConnectionViolation" in repr(v)
        assert "cortex/foo.py" in repr(v)


# ── File Scanning ────────────────────────────────────────────────────────


class TestScanFileLines:
    def test_detects_raw_connect(self, tmp_path):
        py_file = tmp_path / "bad.py"
        py_file.write_text(
            textwrap.dedent("""\
            import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
            conn = sqlite3.connect("test.db")
        """)
        )
        violations = []
        _scan_file_lines(py_file, violations)
        assert len(violations) == 1
        assert violations[0].line_number == 2

    def test_ignores_comments(self, tmp_path):
        py_file = tmp_path / "commented.py"
        py_file.write_text(
            textwrap.dedent("""\
            # conn = sqlite3.connect("test.db")
        """)
        )
        violations = []
        _scan_file_lines(py_file, violations)
        assert len(violations) == 0

    def test_ignores_string_literals(self, tmp_path):
        py_file = tmp_path / "string_literal.py"
        py_file.write_text(
            textwrap.dedent("""\
            msg = "Use sqlite3.connect() to create a connection"
        """)
        )
        violations = []
        _scan_file_lines(py_file, violations)
        assert len(violations) == 0

    def test_detects_multiple_violations(self, tmp_path):
        py_file = tmp_path / "multi.py"
        py_file.write_text(
            textwrap.dedent("""\
            import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
            conn1 = sqlite3.connect("a.db")
            conn2 = sqlite3.connect("b.db")
        """)
        )
        violations = []
        _scan_file_lines(py_file, violations)
        assert len(violations) == 2

    def test_handles_unreadable_file(self, tmp_path):
        py_file = tmp_path / "binary.py"
        py_file.write_bytes(b"\x80\x81\x82\x83")
        violations = []
        _scan_file_lines(py_file, violations)
        assert len(violations) == 0

    def test_clean_file_no_violations(self, tmp_path):
        py_file = tmp_path / "clean.py"
        py_file.write_text(
            textwrap.dedent("""\
            from babylon60.database.core import connect
            conn = connect()
        """)
        )
        violations = []
        _scan_file_lines(py_file, violations)
        assert len(violations) == 0


# ── Full Scanner ─────────────────────────────────────────────────────────


class TestScanRawConnects:
    def test_scan_with_whitelist(self, tmp_path):
        # Create a file that uses raw connect
        module_dir = tmp_path / "cortex"
        module_dir.mkdir()
        bad_file = module_dir / "rogue.py"
        bad_file.write_text("import sqlite3\nconn = sqlite3.connect('x.db')\n")

        violations = scan_raw_connects(root=module_dir, whitelist=frozenset())
        assert len(violations) == 1

    def test_scan_whitelisted_file_ignored(self, tmp_path):
        module_dir = tmp_path / "cortex"
        module_dir.mkdir()
        allowed_file = module_dir / "core.py"
        allowed_file.write_text("import sqlite3\nconn = sqlite3.connect('x.db')\n")

        violations = scan_raw_connects(
            root=module_dir,
            whitelist=frozenset({"cortex/core.py"}),
        )
        assert len(violations) == 0

    def test_scan_skips_test_directory(self, tmp_path):
        module_dir = tmp_path / "cortex"
        tests_dir = module_dir / "tests"
        tests_dir.mkdir(parents=True)
        test_file = tests_dir / "test_db.py"
        test_file.write_text("import sqlite3\nconn = sqlite3.connect(':memory:')\n")

        violations = scan_raw_connects(root=module_dir, whitelist=frozenset())
        assert len(violations) == 0

    def test_scan_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        violations = scan_raw_connects(root=empty_dir)
        assert len(violations) == 0
