"""
Unit tests for HOMER-Ω Worldbuilding Engine.
"""

from __future__ import annotations

import pytest
from labs.homer_engine import (
    ConlangEngine,
    PhoneticInventory,
    MagicAbility,
    MagicResolutionResult,
    NarrativeGraphEvaluator,
    NarrativeNode,
    GeopoliticalEngine,
    ResourceNode,
    Faction,
)


def test_conlang_engine():
    engine = ConlangEngine()
    inventory = PhoneticInventory(
        consonants=["v", "l", "th", "r", "s", "n", "k"],
        vowels=["ae", "i", "o", "u", "e"],
        syllable_templates=["CVC", "CV"],
        illegal_clusters=["vv", "ll", "rr"],
    )
    engine.register_culture("Vaelthari", inventory)

    name = engine.generate_name("Vaelthari", syllable_count=2)
    assert len(name) > 0
    assert engine.validate_name("Vaelthari", name)

    # Test validation error
    with pytest.raises(KeyError):
        engine.generate_name("UnknownCulture")


def test_magic_system():
    # Valid ability
    ability = MagicAbility(
        name="Veilbinding",
        inputs=["spiritual_debt_1"],
        limitations=["cannot_affect_iron"],
        outputs=["invisibility_effect"],
        established_effects=["invisibility_effect"],
        reader_understanding=0.85,
    )
    assert ability.validate() == MagicResolutionResult.VALID
    assert ability.can_resolve_conflict()
    assert ability.sanderson_coefficient() == 1.0

    # Test invalid cases
    no_limits = MagicAbility(
        name="Veilbinding",
        inputs=["spiritual_debt_1"],
        limitations=[],
        outputs=["invisibility_effect"],
        established_effects=["invisibility_effect"],
    )
    assert no_limits.validate() == MagicResolutionResult.DEX_MACHINA
    assert not no_limits.can_resolve_conflict()

    no_inputs = MagicAbility(
        name="Veilbinding",
        inputs=[],
        limitations=["cannot_affect_iron"],
        outputs=["invisibility_effect"],
        established_effects=["invisibility_effect"],
    )
    assert no_inputs.validate() == MagicResolutionResult.COST_UNPAID

    scope_bloat = MagicAbility(
        name="Veilbinding",
        inputs=["spiritual_debt_1"],
        limitations=["cannot_affect_iron"],
        outputs=["supernova"],
        established_effects=["invisibility_effect"],
    )
    assert scope_bloat.validate() == MagicResolutionResult.SCOPE_BLOAT


def test_narrative_graph_evaluator():
    evaluator = NarrativeGraphEvaluator()
    evaluator.set_state("wolf_status", "unknown")

    evaluator.register_node(
        NarrativeNode(
            node_id="start",
            description="Start quest",
            condition=None,
            on_enter=[{"action": "set_flag", "key": "wolf_status", "value": "quest_given"}],
            choices=[{"text": "Next", "next_node": "details"}],
        )
    )

    evaluator.register_node(
        NarrativeNode(
            node_id="details",
            description="Quest details",
            condition='wolf_status == "quest_given"',
            choices=[],
        )
    )

    # Safe AST evaluation logic tests
    assert evaluator.evaluate_condition('wolf_status == "unknown"')
    assert not evaluator.evaluate_condition('wolf_status == "quest_given"')

    # Run enter actions
    evaluator.apply_on_enter("start")
    assert evaluator.evaluate_condition('wolf_status == "quest_given"')

    choices = evaluator.get_available_choices("start")
    assert len(choices) == 1
    assert choices[0]["next_node"] == "details"

    audit_report = evaluator.audit("start")
    assert audit_report["dead_ends"] == ["details"]
    assert audit_report["unreachable_nodes"] == []


def test_geopolitical_engine():
    geo_engine = GeopoliticalEngine(map_size=(5, 5))
    geo_engine.set_cost_at(2, 2, 10.0)

    geo_engine.register_resource(
        ResourceNode(
            name="Lake",
            resource_type="water",
            location=(0, 0),
            abundance=1.0,
        )
    )

    faction_a = Faction(
        name="Aethelgard", capital=(0, 1), influence_radius=3.0, desired_resources=["water"]
    )
    faction_b = Faction(
        name="Vaelthor", capital=(4, 3), influence_radius=3.0, desired_resources=["water"]
    )

    geo_engine.register_faction(faction_a)
    geo_engine.register_faction(faction_b)

    tension = geo_engine.calculate_tension(faction_a, faction_b)
    assert tension > 0.0

    route = geo_engine.find_shortest_trade_route((0, 1), (4, 3))
    assert route is not None
    assert (2, 2) not in route
