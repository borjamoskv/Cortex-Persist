# [C5-REAL] Exergy-Maximized
"""
SimHash Matrix Plagiarism Detector.

Cryptographic and structural evaluation. Uses algorithmic invariants (SimHash)
applied to AST tokens to determine Hamming distance. Triggers a deterministic
plagiarism flag if distance is below the safety threshold.
"""

import ast
import hashlib


class ASTTokenizer(ast.NodeVisitor):
    def __init__(self):
        self.tokens: list[str] = []

    def generic_visit(self, node: ast.AST) -> None:
        self.tokens.append(type(node).__name__)
        super().generic_visit(node)


def get_ast_tokens(code: str) -> list[str]:
    """Converts source code into a stream of AST structural tokens."""
    try:
        tree = ast.parse(code)
        tokenizer = ASTTokenizer()
        tokenizer.visit(tree)
        return tokenizer.tokens
    except SyntaxError:
        return []


def _hash_token(token: str) -> int:
    """Returns a 64-bit integer hash for a token."""
    h = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(h[:8], byteorder="big")


def calculate_simhash(tokens: list[str]) -> int:
    """Calculates the 64-bit SimHash of a sequence of tokens."""
    v = [0] * 64
    for token in tokens:
        h = _hash_token(token)
        for i in range(64):
            bitmask = 1 << i
            if h & bitmask:
                v[i] += 1
            else:
                v[i] -= 1

    simhash = 0
    for i in range(64):
        if v[i] > 0:
            simhash |= 1 << i
    return simhash


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculates Hamming distance between two 64-bit integers."""
    x = hash1 ^ hash2
    return bin(x).count("1")


def detect_plagiarism(code1: str, code2: str, threshold: int = 5) -> dict:
    """
    Evaluates if code1 and code2 are structural plagiarisms.
    Threshold defaults to 5 bits of Hamming distance.
    """
    tokens1 = get_ast_tokens(code1)
    tokens2 = get_ast_tokens(code2)

    if not tokens1 or not tokens2:
        return {
            "plagiarism_flag": False,
            "distance": None,
            "error": "Syntax Error in one or both inputs",
        }

    hash1 = calculate_simhash(tokens1)
    hash2 = calculate_simhash(tokens2)

    distance = hamming_distance(hash1, hash2)

    return {
        "plagiarism_flag": distance <= threshold,
        "distance": distance,
        "hash1": hex(hash1),
        "hash2": hex(hash2),
    }
