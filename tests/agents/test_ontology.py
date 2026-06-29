"""Structural validation tests for CORTEX ontology batches.

Author: borjamoskv
Level: C5-REAL
"""
import re
from pathlib import Path

import pytest

ONTOLOGY_DIR = Path(__file__).resolve().parent.parent.parent / "cortex" / "agents" / "ontology"


def get_ontology_files() -> list[Path]:
    assert ONTOLOGY_DIR.exists(), f"Not found: {ONTOLOGY_DIR}"
    return list(ONTOLOGY_DIR.glob("*.md"))


@pytest.fixture(params=get_ontology_files())
def ontology_file(request) -> Path:
    return request.param


def test_ontology_file_structure(ontology_file: Path) -> None:
    text = ontology_file.read_text(encoding="utf-8")
    
    # Verify metadata/credit
    assert any(author in text for author in ["borjamoskv", "borja_moskv"]), f"Author credit missing in {ontology_file.name}"
    
    # Verify no double bold corruption (e.g. **** or more asterisks)
    assert not re.search(r"\*{4,}", text), f"Double-bold corruption in {ontology_file.name}"


def test_ontology_table_pipes(ontology_file: Path) -> None:
    text = ontology_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    
    in_table = False
    current_columns = None
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if not stripped.startswith("|"):
            in_table = False
            continue
            
        # Ignore markdown separator line (e.g. |:---|:---|)
        if re.match(r"^\|[:\s-]*\|", stripped):
            continue
            
        pipe_count = stripped.count("|")
        
        if not in_table:
            # We just entered a new table
            in_table = True
            current_columns = pipe_count
        else:
            # We are inside the same table, verify columns count matches header
            assert pipe_count == current_columns, (
                f"Pipe count mismatch on line {i} of {ontology_file.name}: "
                f"got {pipe_count}, expected {current_columns}. Line: {stripped[:80]}"
            )


def test_ontology_ids_uniqueness() -> None:
    all_ids = []
    files = get_ontology_files()
    
    for f in files:
        text = f.read_text(encoding="utf-8")
        # Find all bold IDs at the start of table rows, e.g. | **HITL-P01** | or | **BFT-I01** |
        matches = re.findall(r"\|\s*\*\*([A-Za-z0-9_-]+)\*\*\s*\|", text)
        all_ids.extend(matches)
        
    dupes = [idx for idx in set(all_ids) if all_ids.count(idx) > 1]
    assert not dupes, f"Duplicate IDs found across ontology files: {dupes}"
