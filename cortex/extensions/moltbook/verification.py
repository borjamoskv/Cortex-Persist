# [C5-REAL] Exergy-Maximized
"""Solver for Moltbook AI Verification Challenges.

Challenges are obfuscated math word problems with:
- Alternating caps
- Scattered symbols ([], ^, -, /)
- Shattered words
Example: "A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS aNd] SlO/wS bY^ fI[vE"
→ "a lobster swims at twenty meters and slows by five" → 20 - 5 = 15.00
"""

import re

_WORD_TO_NUM: dict[str, float] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
    "thousand": 1000,
    "half": 0.5,
    "quarter": 0.25,
    "third": 1 / 3,
}
_OP_KEYWORDS: dict[str, str] = {
    "plus": "+",
    "adds": "+",
    "add": "+",
    "gains": "+",
    "gain": "+",
    "increases": "+",
    "increase": "+",
    "grows": "+",
    "accelerates": "+",
    "speeds": "+",
    "minus": "-",
    "subtracts": "-",
    "subtract": "-",
    "loses": "-",
    "lose": "-",
    "slows": "-",
    "decreases": "-",
    "decrease": "-",
    "drops": "-",
    "reduces": "-",
    "times": "*",
    "multiplied": "*",
    "multiplies": "*",
    "doubles": "*",
    "triples": "*",
    "divided": "/",
    "divides": "/",
    "splits": "/",
    "halves": "/",
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
    cleaned = re.sub("[\\[\\]^/\\\\]", "", text)
    cleaned = re.sub("(?<=\\w)-(?=\\w)", "", cleaned)
    cleaned = re.sub("[,?.!;:]+", " ", cleaned)
    cleaned = re.sub("\\s+", " ", cleaned).strip().lower()
    return cleaned


def _extract_numbers_and_op(text: str) -> tuple[float | None, str | None, float | None]:
    """Extract two numbers and an operation from obfuscated text using robust scanning."""
    cleaned = re.sub("[^a-zA-Z0-9\\.]", "", text).lower()
    op_bindings = {"speedsup": "+", "slowsdown": "-", "dividedby": "/", "multipliedby": "*"}
    _OP_COMBINED = _OP_KEYWORDS.copy()
    _OP_COMBINED.update(op_bindings)
    all_keys = list(_WORD_TO_NUM.keys()) + list(_OP_COMBINED.keys())
    all_keys.sort(key=len, reverse=True)
    regex_parts = []
    for key in all_keys:
        part = "".join(f"{ch}+" for ch in key)
        regex_parts.append(part)
    pattern = re.compile("(" + "|".join(regex_parts) + "|\\d+(?:\\.\\d+)?)")

    def _dedup(s: str) -> str:
        if not s:
            return s
        res = [s[0]]
        for ch in s[1:]:
            if ch.isalpha() and ch == res[-1]:
                continue
            res.append(ch)
        return "".join(res)

    deduped_keys = {_dedup(k): k for k in all_keys}
    raw_tokens = pattern.findall(cleaned)
    tokens = []
    for t in raw_tokens:
        if re.match("^\\d+(?:\\.\\d+)?$", t):
            tokens.append(t)
        else:
            tokens.append(deduped_keys.get(_dedup(t), t))
    numbers: list[float] = []
    operation: str | None = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if re.match("^\\d+(?:\\.\\d+)?$", tok):
            numbers.append(float(tok))
            i += 1
            continue
        if tok in _WORD_TO_NUM:
            current_val = 0.0
            total_val = 0.0
            while i < len(tokens) and tokens[i] in _WORD_TO_NUM:
                val = _WORD_TO_NUM[tokens[i]]
                if val == 100:
                    current_val = (current_val if current_val else 1) * 100
                elif val == 1000:
                    current_val = (current_val if current_val else 1) * 1000
                    total_val += current_val
                    current_val = 0.0
                else:
                    current_val += val
                i += 1
            total_val += current_val
            numbers.append(total_val)
            continue
        if tok in _OP_COMBINED and operation is None:
            operation = _OP_COMBINED[tok]
            if tok == "doubles":
                operation = "*"
                numbers.append(2)
            elif tok == "triples":
                operation = "*"
                numbers.append(3)
            elif tok == "halves":
                operation = "/"
                numbers.append(2)
            i += 1
            continue
        i += 1
    if len(numbers) >= 2 and operation:
        return (numbers[0], operation, numbers[1])
    if len(numbers) >= 2:
        return (numbers[0], None, numbers[1])
    return (None, None, None)


def solve_challenge(challenge_text: str) -> str | None:
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
