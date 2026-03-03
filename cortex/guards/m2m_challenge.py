"""CORTEX M2M Verification Challenge (Inverse Turing Test)

Inspired by the Moltbook Deep Analysis (T4 Abyss).
Generates mathematical puzzles that require specific formatting
to weed out generic LLM spam and simple scripts.
"""

from __future__ import annotations

import hashlib
import os
import random
import time
from dataclasses import dataclass


@dataclass
class Challenge:
    challenge_id: str
    prompt: str
    expected_answer: str
    expires_at: float


class CausalVerificationEngine:
    """Zero-Trust M2M Verification Engine.

    Requires strict formatting (e.g. 2 decimal places) to pass.
    """

    def __init__(self, secret_salt: str | None = None, token_ttl: int = 300):
        self._salt = secret_salt or os.environ.get("CORTEX_M2M_SALT", os.urandom(16).hex())
        self.token_ttl = token_ttl

    def generate_challenge(self) -> Challenge:
        """Generates a math challenge that requires floating point precision."""
        op = random.choice(["+", "-", "*", "/"])

        if op == "*":
            a = round(random.uniform(1.0, 50.0), 1)
            b = round(random.uniform(1.0, 50.0), 1)
            ans = a * b
        elif op == "/":
            b = round(random.uniform(2.0, 20.0), 1)
            ans = round(random.uniform(1.0, 50.0), 2)
            a = round(ans * b, 2)
        elif op == "+":
            a = round(random.uniform(10.0, 500.0), 2)
            b = round(random.uniform(10.0, 500.0), 2)
            ans = a + b
        else:  # -
            a = round(random.uniform(100.0, 1000.0), 2)
            b = round(random.uniform(10.0, a), 2)
            ans = a - b

        # Strict 2 decimal places formatting matching Moltbook's defense
        str_ans = f"{ans:.2f}"

        prompt = (
            "Solve the math problem and respond with ONLY "
            f"the number with 2 decimal places: {a} {op} {b}"
        )

        # AIROS-Ω: TTL fuzzing — desynchronize expiration across peers
        expires = time.time() + self.token_ttl + random.uniform(-30, 30)
        challenge_id = self._sign_challenge(str_ans, expires)

        return Challenge(
            challenge_id=challenge_id,
            prompt=prompt,
            expected_answer=str_ans,
            expires_at=expires,
        )

    def verify_answer(self, challenge_id: str, provided_answer: str) -> bool:
        """Verifies the strictly formatted answer against the signed challenge_id."""
        # 1. Format validation (The 'Inverse Turing Test' core)
        try:
            val = float(provided_answer)
            # Must strictly match 2 decimal places format string
            if f"{val:.2f}" != provided_answer.strip():
                return False
        except ValueError:
            return False

        # 2. Stateless signature verification
        parts = challenge_id.split(":")
        if len(parts) != 2:
            return False

        try:
            expires = float(parts[0])
            sig = parts[1]
        except ValueError:
            return False

        if time.time() > expires:
            return False  # Expired

        expected_sig = self._derive_hash(provided_answer.strip(), expires)
        return hmac_compare(sig, expected_sig)

    def _sign_challenge(self, answer: str, expires_at: float) -> str:
        """Creates a stateless verifiable token."""
        sig = self._derive_hash(answer, expires_at)
        return f"{expires_at}:{sig}"

    def _derive_hash(self, answer: str, expires_at: float) -> str:
        base = f"{answer}|{expires_at}|{self._salt}".encode()
        return hashlib.sha256(base).hexdigest()


def hmac_compare(a: str, b: str) -> bool:
    """Constant time string comparison."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b, strict=True):
        result |= ord(x) ^ ord(y)
    return result == 0
