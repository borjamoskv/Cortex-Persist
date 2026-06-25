# [C5-REAL] Exergy-Maximized
import pytest

from legacy_research.guards.anergy_honeypot import AnergyHoneypotGuard


def test_anergy_honeypot_clean_claims():
    """Verify that pure structural claims do not trigger the honeypot."""
    honeypot = AnergyHoneypotGuard(difficulty_prefix="0")
    # Should not raise any exception
    honeypot.evaluate_payload(["Valid structural claim", "Another Exergy dense fact."])


def test_anergy_honeypot_triggers_on_green_theater():
    """Verify that limerent phrases trigger the computational burn and reject the payload."""
    honeypot = AnergyHoneypotGuard(difficulty_prefix="0")  # Set easy difficulty so test doesn't hang
    
    with pytest.raises(ValueError, match="MTK-REJECT: Anergy Honeypot triggered"):
        honeypot.evaluate_payload([
            "Here is the code you requested",
            "I apologize, as an AI language model..."
        ], agent_id="STOCHASTIC-PARROT")


def test_anergy_honeypot_case_insensitive():
    """Verify that the matching is case insensitive."""
    honeypot = AnergyHoneypotGuard(difficulty_prefix="0")
    
    with pytest.raises(ValueError, match="MTK-REJECT: Anergy Honeypot triggered"):
        honeypot.evaluate_payload(["ESPERO QUE ESTO AYUDE a resolver el problema."])
