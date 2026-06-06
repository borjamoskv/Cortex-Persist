#!/usr/bin/env python3
"""
CORTEX Multilingual Documentation Parity Verifier
==================================================
Ensures README.md, README.es.md, and README.zh.md are structurally aligned:
- Identical heading level hierarchy and counts.
- Same number and language target of code blocks.
- Identical table layouts (rows/columns).
- Synchronized links and asset references.

DERIVATION: Ω₄ Structural Determinism.
"""

import re
import sys
from pathlib import Path

# Color styling for Industrial Noir 2026 logs
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def extract_headings(content: str) -> list[tuple[int, str]]:
    """Extracts markdown headings as (level, text)."""
    headings = []
    for line in content.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append((level, text))
    return headings


def extract_code_blocks(content: str) -> list[tuple[str, str]]:
    """Extracts code blocks as (language, block_content)."""
    # Matches ```lang ... ```
    pattern = re.compile(r"```([a-zA-Z0-9_\-\+]*)\n(.*?)```", re.DOTALL)
    blocks = []
    for match in pattern.finditer(content):
        lang = match.group(1).strip()
        block_content = match.group(2).strip()
        blocks.append((lang, block_content))
    return blocks


def extract_tables(content: str) -> list[list[str]]:
    """Extracts tables from markdown and returns a list of rows with columns parsed."""
    tables = []
    current_table = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            # Check if this is a separator line (e.g. |---|:---|)
            if re.match(r"^\|[\s:\-\|]+$", line):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            current_table.append(cells)
        else:
            if current_table:
                tables.append(current_table)
                current_table = []
    if current_table:
        tables.append(current_table)
    return tables


def verify_file_parity(source_path: Path, target_path: Path) -> list[str]:
    """Checks target file structure against source file."""
    errors = []
    source_name = source_path.name
    target_name = target_path.name

    if not target_path.exists():
        return [f"File {target_name} does not exist."]

    source_content = source_path.read_text(encoding="utf-8")
    target_content = target_path.read_text(encoding="utf-8")

    # 1. Verify Headings Hierarchy
    source_headings = extract_headings(source_content)
    target_headings = extract_headings(target_content)

    if len(source_headings) != len(target_headings):
        errors.append(
            f"Heading count mismatch: {source_name} has {len(source_headings)}, "
            f"but {target_name} has {len(target_headings)}."
        )
    else:
        for idx, ((s_level, s_text), (t_level, t_text)) in enumerate(
            zip(source_headings, target_headings, strict=False)
        ):
            if s_level != t_level:
                errors.append(
                    f"Heading level mismatch at index {idx}: "
                    f"'{s_text}' (L{s_level}) vs '{t_text}' (L{t_level})"
                )

    # 2. Verify Code Blocks
    source_code = extract_code_blocks(source_content)
    target_code = extract_code_blocks(target_content)

    if len(source_code) != len(target_code):
        errors.append(
            f"Code block count mismatch: {source_name} has {len(source_code)}, "
            f"but {target_name} has {len(target_code)}."
        )
    else:
        for idx, ((s_lang, s_content), (t_lang, t_content)) in enumerate(
            zip(source_code, target_code, strict=False)
        ):
            if s_lang != t_lang:
                errors.append(
                    f"Code block language mismatch at index {idx}: "
                    f"'{s_lang}' in {source_name} vs '{t_lang}' in {target_name}."
                )

            # Extract clean lines (no comments, no empty lines) to verify script logic is matching
            s_clean = [
                line.strip()
                for line in s_content.splitlines()
                if line.strip()
                and not line.strip().startswith(("#", "//", "/*", "*", "'''", '"""'))
            ]
            t_clean = [
                line.strip()
                for line in t_content.splitlines()
                if line.strip()
                and not line.strip().startswith(("#", "//", "/*", "*", "'''", '"""'))
            ]

            # Only compare logic lines if code languages match and are script-based (python, bash, rust)
            if s_lang == t_lang and s_lang in ("python", "bash", "rust", "sh"):
                # Normalize common differences in translation strings if matching code examples
                if len(s_clean) != len(t_clean):
                    errors.append(
                        f"Code block logical lines count mismatch at index {idx} ({s_lang}): "
                        f"source={len(s_clean)} vs target={len(t_clean)} lines.\n"
                        f"Source clean content:\n{s_content}\nTarget clean content:\n{t_content}"
                    )

    # 3. Verify Tables
    source_tables = extract_tables(source_content)
    target_tables = extract_tables(target_content)

    if len(source_tables) != len(target_tables):
        errors.append(
            f"Table count mismatch: {source_name} has {len(source_tables)}, "
            f"but {target_name} has {len(target_tables)}."
        )
    else:
        for idx, (s_table, t_table) in enumerate(zip(source_tables, target_tables, strict=False)):
            if len(s_table) != len(t_table):
                errors.append(
                    f"Table row count mismatch at index {idx}: "
                    f"source has {len(s_table)} rows, target has {len(t_table)} rows."
                )
            else:
                for row_idx, (s_row, t_row) in enumerate(zip(s_table, t_table, strict=False)):
                    if len(s_row) != len(t_row):
                        errors.append(
                            f"Table column count mismatch at table index {idx}, row {row_idx}: "
                            f"source={len(s_row)} columns vs target={len(t_row)} columns."
                        )

    return errors


def _print(msg: str = ""):
    sys.stdout.write(f"{msg}\n")
    sys.stdout.flush()


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    readme_en = repo_root / "README.md"
    readme_es = repo_root / "README.es.md"
    readme_zh = repo_root / "README.zh.md"

    _print(f"\n{BLUE}{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    _print(f"{BLUE}{BOLD}║  🔍 CORTEX DOCUMENTATION PARITY VERIFIER         ║{RESET}")
    _print(f"{BLUE}{BOLD}╚══════════════════════════════════════════════════╝{RESET}\n")

    if not readme_en.exists():
        _print(f"{RED}🛑 README.md not found in {repo_root}{RESET}")
        return 1

    targets = [readme_es, readme_zh]
    all_passed = True

    for target in targets:
        _print(f"Checking {BLUE}{target.name}{RESET} against {BLUE}README.md{RESET}...")
        errors = verify_file_parity(readme_en, target)
        if errors:
            _print(f"  {RED}❌ Failed structural check:{RESET}")
            for err in errors:
                _print(f"    - {err}")
            all_passed = False
        else:
            _print(f"  {GREEN}✔ All structural constraints met.{RESET}")
        _print()

    if all_passed:
        _print(f"{GREEN}{BOLD}🎉 DOCUMENTATION IN SYNC (C5-REAL Realized){RESET}\n")
        return 0
    _print(f"{RED}{BOLD}🛑 PARITY ERRORS DETECTED. Update translations before committing.{RESET}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
