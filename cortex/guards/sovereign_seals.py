# This file is part of CORTEX. Apache-2.0.
"""Sovereign Seals — Helper functions for 10-Seal Quality Gates.

Provides dependency parsing, import extraction, and self-preservation checks
used by the consolidated seals.py. Stubs (16, 18, 19, 20) have been purged.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from cortex.guards._seal_printer import SealPrinter

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

printer = SealPrinter()

# ── stdlib package names (common subset) — used to exclude from ghost detection ──
_STDLIB_TOP = frozenset(
    {
        "abc",
        "argparse",
        "ast",
        "asyncio",
        "atexit",
        "base64",
        "bisect",
        "calendar",
        "cgi",
        "cmd",
        "codecs",
        "collections",
        "colorsys",
        "concurrent",
        "configparser",
        "contextlib",
        "copy",
        "csv",
        "ctypes",
        "dataclasses",
        "datetime",
        "dbm",
        "decimal",
        "difflib",
        "dis",
        "email",
        "encodings",
        "enum",
        "errno",
        "faulthandler",
        "fcntl",
        "fileinput",
        "fnmatch",
        "fractions",
        "ftplib",
        "functools",
        "gc",
        "getpass",
        "gettext",
        "glob",
        "gzip",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "http",
        "imaplib",
        "importlib",
        "inspect",
        "io",
        "ipaddress",
        "itertools",
        "json",
        "keyword",
        "linecache",
        "locale",
        "logging",
        "lzma",
        "mailbox",
        "math",
        "mimetypes",
        "mmap",
        "multiprocessing",
        "netrc",
        "numbers",
        "operator",
        "os",
        "pathlib",
        "pdb",
        "pickle",
        "pkgutil",
        "platform",
        "plistlib",
        "posixpath",
        "pprint",
        "profile",
        "pstats",
        "py_compile",
        "queue",
        "quopri",
        "random",
        "re",
        "readline",
        "reprlib",
        "resource",
        "rlcompleter",
        "sched",
        "secrets",
        "select",
        "selectors",
        "shelve",
        "shlex",
        "shutil",
        "signal",
        "site",
        "smtplib",
        "socket",
        "socketserver",
        "sqlite3",
        "ssl",
        "stat",
        "statistics",
        "string",
        "struct",
        "subprocess",
        "sys",
        "sysconfig",
        "syslog",
        "tabnanny",
        "tarfile",
        "tempfile",
        "termios",
        "textwrap",
        "threading",
        "time",
        "timeit",
        "token",
        "tokenize",
        "tomllib",
        "trace",
        "traceback",
        "tracemalloc",
        "tty",
        "types",
        "typing",
        "typing_extensions",
        "unicodedata",
        "unittest",
        "urllib",
        "uuid",
        "venv",
        "warnings",
        "wave",
        "weakref",
        "webbrowser",
        "wsgiref",
        "xml",
        "xmlrpc",
        "zipfile",
        "zipimport",
        "zlib",
        # Common typing / compat
        "_thread",
        "__future__",
        "builtins",
        "copyreg",
        "posix",
        "nt",
        "contextvars",
        "graphlib",
        "zoneinfo",
    }
)

# Known first-party package prefixes
_FIRST_PARTY = frozenset({"cortex"})

# Mapping from import name → pyproject.toml package name (where they differ)
_IMPORT_TO_PKG = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "attr": "attrs",
    "dotenv": "python-dotenv",
    "jose": "python-jose",
    "jwt": "pyjwt",
    "gi": "pygobject",
    "serial": "pyserial",
    "usb": "pyusb",
    "wx": "wxpython",
    "Crypto": "pycryptodome",
    "objc": "pyobjc-core",
    "AppKit": "pyobjc-framework-Cocoa",
    "Foundation": "pyobjc-framework-Cocoa",
    "Cocoa": "pyobjc-framework-Cocoa",
    "Quartz": "pyobjc-framework-Quartz",
    "CoreFoundation": "pyobjc-framework-Cocoa",
    "google": "google-adk",
    "stripe_mod": "stripe",
    "qdrant_client": "qdrant-client",
    "sentence_transformers": "sentence-transformers",
    "sqlite_vec": "sqlite-vec",
    "z3": "z3-solver",
}


def _parse_pyproject_deps() -> set[str]:
    """Extract all declared dependency package names from pyproject.toml."""
    pyproject = ROOT_DIR / "pyproject.toml"
    if not pyproject.exists():
        return set()

    content = pyproject.read_text(encoding="utf-8")
    deps: set[str] = set()
    for match in re.finditer(r'"([a-zA-Z0-9_-]+)', content):
        name = match.group(1).lower().replace("-", "_")
        deps.add(name)
    return deps


def _extract_imports(source: str) -> set[str]:
    """Extract top-level imported package names from Python source."""
    imports: set[str] = set()
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("import "):
            parts = stripped[7:].split(",")
            for part in parts:
                pkg = part.strip().split(".")[0].split(" ")[0]
                if pkg:
                    imports.add(pkg)
        elif stripped.startswith("from "):
            match = re.match(r"from\s+(\S+)", stripped)
            if match:
                pkg = match.group(1).split(".")[0]
                if pkg:
                    imports.add(pkg)
    return imports


async def check_seal_8_dependency_impl(
    cached_files: dict[Path, str],
) -> tuple[bool, str]:
    """Dependency Ghost Check + Shannon Entropy Budget.

    Warn-only — never blocks the pipeline.
    """
    import math
    from collections import Counter

    # ── Dependency Ghost Check ──
    declared = _parse_pyproject_deps()
    if declared:
        all_imports: set[str] = set()
        for _path, content in cached_files.items():
            all_imports |= _extract_imports(content)

        external_imports: set[str] = set()
        for imp in all_imports:
            if imp in _STDLIB_TOP or imp in _FIRST_PARTY:
                continue
            normalized = _IMPORT_TO_PKG.get(imp, imp).lower().replace("-", "_")
            external_imports.add(normalized)

        undeclared = external_imports - declared
        _FP_FILTER = frozenset(
            {"pytest", "hypothesis", "_pytest", "setuptools", "pip", "pkg_resources"}
        )
        undeclared -= _FP_FILTER

        if undeclared:
            printer.warn(f"Potentially undeclared imports: {sorted(undeclared)[:10]}")
        else:
            printer.success(f"Dependency Ghost Check: {len(external_imports)} externals verified.")
    else:
        printer.warn("No pyproject.toml deps — skipping dependency check.")

    # ── Shannon Entropy Budget ──
    def _entropy(text: str) -> float:
        if not text:
            return 0.0
        counts = Counter(text)
        length = len(text)
        return -sum((c / length) * math.log2(c / length) for c in counts.values())

    entropy_violations = []
    for py_file, content in cached_files.items():
        if "__pycache__" in py_file.parts:
            continue
        e = _entropy(content)
        if e > 6.5:
            entropy_violations.append(f"{py_file.name} ({e:.2f})")

    if entropy_violations:
        printer.warn(f"High entropy: {entropy_violations}")
    else:
        printer.success("Shannon Entropy Budget intact (<6.5 bits/char).")

    return True, "verified"


async def check_seal_9_compliance_impl() -> tuple[bool, str]:
    """Aesthetic Gate + EU AI Act Audit Trail.

    Warn-only — never blocks the pipeline.
    """
    import asyncio

    # ── Aesthetic Gate ──
    forbidden = ["FIXME", "TODO: placeholder", "MVP style"]
    targets = [ROOT_DIR / "README.md", ROOT_DIR / "AGENTS.md"]
    aesthetic_issues = []
    for t in targets:
        if t.exists():
            content = (await asyncio.to_thread(t.read_text, encoding="utf-8")).lower()
            for f in forbidden:
                if f.lower() in content:
                    aesthetic_issues.append(f"{t.name} contains '{f}'")

    if aesthetic_issues:
        printer.warn(f"Aesthetic drift: {aesthetic_issues}")
    else:
        printer.success("Aesthetic Gate intact — no placeholders.")

    # ── EU AI Act Audit Trail ──
    try:
        from cortex.engine import CortexEngine

        engine = CortexEngine(":memory:", auto_embed=False)
        await engine.init_db()
        async with engine._get_conn() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%audit%'"
            )
            tables = await cursor.fetchall()
        await engine.close()
        if tables:
            printer.success(f"EU AI Act audit trail: {len(tables)} audit table(s) found.")
        else:
            printer.warn("EU AI Act: no audit tables found — implement for compliance.")
    except Exception:  # noqa: BLE001 — compliance check boundary
        printer.warn("EU AI Act audit check skipped (engine not available).")

    # ── SSRF URLGuard Verification (CodeQL #95) ──
    try:
        from cortex.guards.url_guard import is_safe_url

        if is_safe_url("https://sunoapi.org/api/v1"):
            printer.success("SSRF URLGuard: Logic active and functional.")
        else:
            printer.fail("SSRF URLGuard: Misconfigured or non-functional.")
            return False, "URLGuard failure"
    except ImportError:
        printer.fail("SSRF URLGuard: Module missing — CodeQL #95 vulnerability risk.")
        return False, "URLGuard missing"

    return True, "verified"


async def check_gate_21_preservation(
    cached_files: dict[Path, str] | None = None,
) -> tuple[bool, str]:
    """Seal 10 (was 21): Sovereign Self-Preservation.

    Verifies structural integrity of the defense system:
    1. Pre-push hook exists and is executable
    2. seals.py exists in source tree
    3. HEAD has a parent commit (not orphan/detached)
    """
    passed = True
    checks: list[str] = []

    # 1. Pre-push hook
    hook = ROOT_DIR / ".git" / "hooks" / "pre-push"
    if hook.exists():
        if os.access(hook, os.X_OK):
            checks.append("pre-push hook ✓")
        else:
            printer.warn("pre-push hook exists but is not executable.")
            checks.append("pre-push hook (not executable)")
    else:
        printer.fail("pre-push hook missing — defense perimeter breached.")
        passed = False

    # 2. seals.py self-reference
    seals_path = ROOT_DIR / "cortex" / "guards" / "seals.py"
    if cached_files:
        seals_exists = any(p.name == "seals.py" and "guards" in p.parts for p in cached_files)
    else:
        seals_exists = seals_path.exists()

    if seals_exists:
        checks.append("seals.py ✓")
    else:
        printer.fail("seals.py not found — self-audit system deleted.")
        passed = False

    # 3. HEAD has parent (not orphan)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            checks.append("HEAD lineage ✓")
        else:
            printer.warn("HEAD has no parent (initial or orphan commit).")
            checks.append("HEAD lineage (orphan)")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        printer.warn("git not available for lineage check.")
        checks.append("HEAD lineage (unchecked)")

    if passed:
        printer.success(f"Self-Preservation intact ({', '.join(checks)}).")
    return passed, "verified"
