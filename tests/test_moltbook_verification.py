"""Tests for the Moltbook verification challenge solver."""

import pytest
from cortex.moltbook.verification import solve_challenge, _strip_obfuscation


class TestStripObfuscation:
    """Test the obfuscation stripping."""

    def test_removes_brackets(self):
        assert _strip_obfuscation("h[el]lo") == "hello"

    def test_removes_carets(self):
        assert _strip_obfuscation("he^llo") == "hello"

    def test_removes_slashes(self):
        assert _strip_obfuscation("he/llo") == "hello"

    def test_joins_hyphenated_words(self):
        assert _strip_obfuscation("tW-eNn-Tyy") == "twenntyy"

    def test_normalizes_case(self):
        assert _strip_obfuscation("HeLLo WoRLd") == "hello world"

    def test_collapses_whitespace(self):
        assert _strip_obfuscation("  hello   world  ") == "hello world"

    def test_full_obfuscated_text(self):
        text = "A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy"
        result = _strip_obfuscation(text)
        assert "lobster" in result
        assert "swims" in result


class TestSolveChallenge:
    """Test challenge solving with various obfuscated math problems."""

    def test_subtraction_twenty_minus_five(self):
        challenge = (
            "A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS "
            "aNd] SlO/wS bY^ fI[vE, wH-aTs] ThE/ nEw^ SpE[eD?"
        )
        answer = solve_challenge(challenge)
        assert answer == "15.00"

    def test_addition_simple(self):
        challenge = "a lobster has ten shells and gains five more"
        assert solve_challenge(challenge) == "15.00"

    def test_multiplication(self):
        challenge = "a lobster weighs three kilos times four"
        assert solve_challenge(challenge) == "12.00"

    def test_division(self):
        challenge = "twenty lobsters divided by five groups"
        assert solve_challenge(challenge) == "4.00"

    def test_larger_numbers(self):
        challenge = "a lobster swims at fifty meters and slows by thirty"
        assert solve_challenge(challenge) == "20.00"

    def test_compound_number_twenty_five(self):
        challenge = "twenty five lobsters plus ten more"
        assert solve_challenge(challenge) == "35.00"

    def test_result_with_decimals(self):
        challenge = "seven lobsters divided by two groups"
        assert solve_challenge(challenge) == "3.50"

    def test_heavily_obfuscated(self):
        challenge = "tH^iR[tE-eN] lO/bS^tE[rS pL]uS/ tW^eN[tY"
        answer = solve_challenge(challenge)
        assert answer == "33.00"

    def test_returns_none_for_garbage(self):
        assert solve_challenge("this has no numbers at all") is None

    def test_numeric_literals_in_text(self):
        challenge = "a lobster at 20 meters slows by 5"
        assert solve_challenge(challenge) == "15.00"

    def test_doubles_keyword(self):
        challenge = "a lobster weighing eight kilos doubles"
        assert solve_challenge(challenge) == "16.00"

    def test_zero_result(self):
        challenge = "five lobsters minus five"
        assert solve_challenge(challenge) == "0.00"
