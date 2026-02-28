"""Solver for Moltbook AI Verification Challenges.

Challenges are obfuscated math word problems with:
- Alternating caps
- Scattered symbols ([], ^, -, /)
- Shattered words
Example: "A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS aNd] SlO/wS bY^ fI[vE"
→ "a lobster swims at twenty meters and slows by five" → 20 - 5 = 15.00
"""

from __future__ import annotations

import re
from typing import Optional

# Number words → numeric values (covers typical Moltbook range)
_WORD_TO_NUM: dict[str, float] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    "half": 0.5, "quarter": 0.25, "third": 1 / 3,
}

# Operation keywords → operator
_OP_KEYWORDS: dict[str, str] = {
    "plus": "+", "adds": "+", "add": "+", "gains": "+", "gain": "+",
    "increases": "+", "increase": "+", "grows": "+", "accelerates": "+",
    "speeds": "+",
    "minus": "-", "subtracts": "-", "subtract": "-", "loses": "-",
    "lose": "-", "slows": "-", "decreases": "-", "decrease": "-",
    "drops": "-", "reduces": "-",
    "times": "*", "multiplied": "*", "multiplies": "*", "doubles": "*",
    "triples": "*",
    "divided": "/", "divides": "/", "splits": "/", "halves": "/",
}


def _deduplicate_letters(word: str) -> str:
    """Collapse consecutive duplicate letters: 'twenntyy' → 'twenty'."""
    if not word:
        return word
    result = [word[0]]
    for ch in word[1:]:
        if ch != result[-1]:
            result.append(ch)
    return "".join(result)


def _fuzzy_word_lookup(word: str) -> float | None:
    """Try to match a word to a number, handling obfuscation artifacts."""
    if word in _WORD_TO_NUM:
        return _WORD_TO_NUM[word]
    deduped = _deduplicate_letters(word)
    if deduped in _WORD_TO_NUM:
        return _WORD_TO_NUM[deduped]
    return None


def _strip_obfuscation(text: str) -> str:
    """Remove obfuscation symbols and normalize to lowercase."""
    # Strip brackets, carets, slashes, hyphens used as obfuscation
    cleaned = re.sub(r"[\[\]^/\\]", "", text)
    # Collapse hyphens between word chars (shattered words)
    cleaned = re.sub(r"(?<=\w)-(?=\w)", "", cleaned)
    # Remove punctuation attached to words (commas, periods, question marks)
    cleaned = re.sub(r"[,?.!;:]+", " ", cleaned)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _parse_compound_number(words: list[str], start: int) -> tuple[float, int]:
    """Parse compound number words like 'twenty five' or 'three hundred'.
    
    Returns (value, number_of_words_consumed).
    """
    if start >= len(words):
        return (0.0, 0)

    total = 0.0
    current = 0.0
    consumed = 0

    i = start
    while i < len(words):
        word = words[i]
        if _fuzzy_word_lookup(word) is None:
            break

        val = _fuzzy_word_lookup(word)  # type: ignore[assignment]

        if val == 100:
            current = (current if current else 1) * 100
        elif val == 1000:
            current = (current if current else 1) * 1000
            total += current
            current = 0.0
        else:
            current += val

        consumed += 1
        i += 1

    total += current
    return (total, consumed)


def _extract_numbers_and_op(text: str) -> tuple[Optional[float], Optional[str], Optional[float]]:
    """Extract two numbers and an operation from decoded text."""
    words = text.split()
    numbers: list[float] = []
    operation: Optional[str] = None

    i = 0
    while i < len(words):
        word = words[i]

        # Check for numeric literals
        try:
            numbers.append(float(word))
            i += 1
            continue
        except ValueError:
            pass

        # Check for number words (with fuzzy matching for obfuscation)
        if _fuzzy_word_lookup(word) is not None:
            val, consumed = _parse_compound_number(words, i)
            numbers.append(val)
            i += consumed
            continue

        # Check for operation keywords (also try deduplicated)
        op_word = word if word in _OP_KEYWORDS else _deduplicate_letters(word)
        if op_word in _OP_KEYWORDS and operation is None:
            operation = _OP_KEYWORDS[op_word]
            # Special case: "doubles" = *2, "triples" = *3, "halves" = /2
            if op_word == "doubles":
                operation = "*"
                numbers.append(2)
            elif op_word == "triples":
                operation = "*"
                numbers.append(3)
            elif op_word == "halves":
                operation = "/"
                numbers.append(2)
            i += 1
            continue

        # Check multi-word ops: "divided by", "multiplied by", "speeds up by"
        if i + 1 < len(words):
            bigram = f"{word} {words[i + 1]}"
            if bigram in ("divided by", "multiplied by"):
                operation = _OP_KEYWORDS.get(word, None)
                i += 2
                continue
            if bigram in ("speeds up", "slows down"):
                operation = _OP_KEYWORDS.get(word, None)
                i += 2
                # skip "by" if present
                if i < len(words) and words[i] == "by":
                    i += 1
                continue

        i += 1

    if len(numbers) >= 2 and operation:
        return (numbers[0], operation, numbers[1])
    if len(numbers) >= 2:
        # Default guess: could be addition context
        return (numbers[0], None, numbers[1])
    return (None, None, None)


def solve_challenge(challenge_text: str) -> Optional[str]:
    """Solve a Moltbook verification challenge.

    Args:
        challenge_text: The obfuscated challenge string from the API.

    Returns:
        Answer formatted to 2 decimal places, or None if unsolvable.
    """
    decoded = _strip_obfuscation(challenge_text)
    num1, op, num2 = _extract_numbers_and_op(decoded)

    if num1 is None or num2 is None or op is None:
        return None

    ops = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a / b if b != 0 else None,
    }

    calculator = ops.get(op)
    if calculator is None:
        return None

    result = calculator(num1, num2)
    if result is None:
        return None

    return f"{result:.2f}"
