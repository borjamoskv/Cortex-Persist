"""Structural validation tests for APEX_CORE registry.

Author: borjamoskv
Level: C5-REAL
"""
import json
import re
from pathlib import Path

import pytest

REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "cortex" / "agents" / "primitives"
APEX_CORE_MD = REGISTRY_DIR / "APEX_CORE.md"
APEX_REGISTRY_JSON = REGISTRY_DIR / "apex_registry_100.json"


@pytest.fixture
def registry_json() -> dict:
    assert APEX_REGISTRY_JSON.exists(), f"Not found: {APEX_REGISTRY_JSON}"
    return json.loads(APEX_REGISTRY_JSON.read_text(encoding="utf-8"))


@pytest.fixture
def apex_core_text() -> str:
    assert APEX_CORE_MD.exists(), f"Not found: {APEX_CORE_MD}"
    return APEX_CORE_MD.read_text(encoding="utf-8")


class TestRegistryCounts:
    def test_primitives_count(self, registry_json: dict) -> None:
        assert len(registry_json["primitives"]) == 100

    def test_invariants_count(self, registry_json: dict) -> None:
        assert len(registry_json["invariants"]) == 100

    def test_antipatterns_count(self, registry_json: dict) -> None:
        assert len(registry_json["antipatterns"]) == 23

    def test_redundancies_count(self, registry_json: dict) -> None:
        assert len(registry_json["redundancies"]) == 11

    def test_meta_counts_match(self, registry_json: dict) -> None:
        meta = registry_json["meta"]["counts"]
        assert meta["primitives"] == len(registry_json["primitives"])
        assert meta["invariants"] == len(registry_json["invariants"])
        assert meta["antipatterns"] == len(registry_json["antipatterns"])
        assert meta["redundancies"] == len(registry_json["redundancies"])


class TestIDContiguity:
    def test_primitive_ids_contiguous(self, registry_json: dict) -> None:
        ids = sorted(int(p["id"].replace("APEX-", "")) for p in registry_json["primitives"])
        assert ids == list(range(1, 101))

    def test_invariant_ids_contiguous(self, registry_json: dict) -> None:
        ids = sorted(int(i["id"].replace("OUROBOROS-", "")) for i in registry_json["invariants"])
        assert ids == list(range(1, 101))

    def test_antipattern_ids_contiguous(self, registry_json: dict) -> None:
        ids = sorted(int(a["id"].replace("AP-", "")) for a in registry_json["antipatterns"])
        assert ids == list(range(1, 24))

    def test_redundancy_ids_contiguous(self, registry_json: dict) -> None:
        ids = sorted(int(r["id"].replace("RA-", "")) for r in registry_json["redundancies"])
        assert ids == list(range(1, 12))


class TestUniqueness:
    def test_opcode_uniqueness(self, registry_json: dict) -> None:
        opcodes = [p["opcode"] for p in registry_json["primitives"]]
        dupes = [o for o in set(opcodes) if opcodes.count(o) > 1]
        assert not dupes, f"Duplicate opcodes: {dupes}"

    def test_invariant_name_uniqueness(self, registry_json: dict) -> None:
        names = []
        for inv in registry_json["invariants"]:
            name = inv["name"]
            base = name.split(":")[0].strip() if ":" in name else name
            names.append(base)
        dupes = [n for n in set(names) if names.count(n) > 1]
        assert not dupes, f"Duplicate invariant names: {dupes}"


class TestMarkdownIntegrity:
    def test_no_double_bold_corruption(self, apex_core_text: str) -> None:
        matches = re.findall(r"\*{4,}", apex_core_text)
        assert len(matches) == 0, f"Double-bold corruption: {len(matches)} occurrences"

    def test_no_broken_pipes_primitives(self, apex_core_text: str) -> None:
        broken = []
        for i, line in enumerate(apex_core_text.splitlines(), 1):
            if line.startswith("| **APEX-"):
                if line.count("|") != 7:
                    broken.append((i, line.count("|"), line[:80]))
        assert not broken, f"Broken primitive rows: {broken}"

    def test_no_broken_pipes_invariants(self, apex_core_text: str) -> None:
        broken = []
        for i, line in enumerate(apex_core_text.splitlines(), 1):
            if line.startswith("| **OUROBOROS-"):
                if line.count("|") != 5:
                    broken.append((i, line.count("|"), line[:80]))
        assert not broken, f"Broken invariant rows: {broken}"

    def test_primitive_count_in_markdown(self, apex_core_text: str) -> None:
        count = len(re.findall(r"\| \*\*APEX-\d+\*\*", apex_core_text))
        assert count == 100, f"Expected 100 primitives in MD, got {count}"

    def test_invariant_count_in_markdown(self, apex_core_text: str) -> None:
        count = len(re.findall(r"\| \*\*OUROBOROS-\d+\*\*", apex_core_text))
        assert count == 100, f"Expected 100 invariants in MD, got {count}"


class TestForgeIdempotency:
    def test_forge_parse_roundtrip(self) -> None:
        from cortex.agents.primitives.apex_forge import (
            parse_apex_core,
            select_canonical,
        )
        report = parse_apex_core(APEX_CORE_MD)
        canonical = select_canonical(report)
        assert len(canonical.primitives) == 100
        assert len(canonical.invariants) == 100
        assert len(canonical.antipatterns) == 23
        assert len(canonical.redundancies) == 11


class TestDemiurgeCredit:
    def test_author_in_json_meta(self, registry_json: dict) -> None:
        assert registry_json["meta"]["author"] == "borjamoskv"

    def test_demiurge_primitive_exists(self, registry_json: dict) -> None:
        demiurge = [p for p in registry_json["primitives"] if "DEMIURGE" in p["opcode"]]
        assert len(demiurge) >= 1
