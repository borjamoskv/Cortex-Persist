"""Tests for the Specialist Roster — Zero-Trust validation of agent definitions."""

import re
import pytest
from moltbook.specialist_roster import (
    SPECIALISTS,
    SPECIALIST_BY_NAME,
    get_specialist,
    all_specialist_names,
    specialists_for_submolt,
    SpecialistProfile,
)


# ─── Valid name pattern: lowercase alphanumeric + hyphens ────────────────
_VALID_NAME = re.compile(r"^[a-z][a-z0-9\-]+$")


class TestRosterIntegrity:
    """Ensure every specialist has required fields and valid data."""

    def test_roster_has_8_specialists(self):
        assert len(SPECIALISTS) == 8

    def test_no_duplicate_names(self):
        names = [s.name for s in SPECIALISTS]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_no_duplicate_specialties(self):
        specs = [s.specialty for s in SPECIALISTS]
        assert len(specs) == len(set(specs)), f"Duplicate specialties: {specs}"

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=lambda s: s.name)
    def test_name_format_valid(self, specialist):
        assert _VALID_NAME.match(specialist.name), \
            f"Invalid name format: {specialist.name}"

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=lambda s: s.name)
    def test_required_fields_present(self, specialist):
        assert specialist.name, "name is empty"
        assert specialist.display_name, "display_name is empty"
        assert specialist.specialty, "specialty is empty"
        assert len(specialist.bio) >= 50, f"bio too short ({len(specialist.bio)} chars)"
        assert len(specialist.persona_prompt) >= 100, \
            f"persona_prompt too short ({len(specialist.persona_prompt)} chars)"
        assert len(specialist.expertise_keywords) >= 5, \
            f"Need ≥5 keywords, got {len(specialist.expertise_keywords)}"
        assert len(specialist.target_submolts) >= 2, \
            f"Need ≥2 submolts, got {len(specialist.target_submolts)}"
        assert specialist.voice_angle, "voice_angle is empty"

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=lambda s: s.name)
    def test_bio_length_optimal(self, specialist):
        """Moltbook bios should be 100-300 chars for optimal display."""
        assert 50 <= len(specialist.bio) <= 400, \
            f"Bio length {len(specialist.bio)} outside optimal range"

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=lambda s: s.name)
    def test_immutability(self, specialist):
        """SpecialistProfile is frozen — no mutation allowed."""
        with pytest.raises(AttributeError):
            specialist.name = "hacked"


class TestLookupHelpers:
    """Test O(1) lookups and filtering."""

    def test_get_specialist_found(self):
        result = get_specialist("cortex-memory-architect")
        assert result is not None
        assert result.specialty == "memory_persistence"

    def test_get_specialist_not_found(self):
        assert get_specialist("nonexistent-agent") is None

    def test_all_specialist_names(self):
        names = all_specialist_names()
        assert len(names) == 8
        assert all(isinstance(n, str) for n in names)

    def test_specialists_for_submolt(self):
        agents_submolt = specialists_for_submolt("agents")
        # Most specialists target 'agents'
        assert len(agents_submolt) >= 6

    def test_specialist_by_name_dict(self):
        assert len(SPECIALIST_BY_NAME) == 8
        assert "cortex-security-auditor" in SPECIALIST_BY_NAME

    def test_specialists_cover_all_key_submolts(self):
        """Verify coverage across important Moltbook communities."""
        all_submolts: set[str] = set()
        for s in SPECIALISTS:
            all_submolts.update(s.target_submolts)
        assert "agents" in all_submolts
        assert "ai" in all_submolts
        assert "security" in all_submolts
        assert "ml" in all_submolts
