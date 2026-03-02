"""
Cognitive Engine - AST Analysis and Intent Prediction.
Ω₂: Deep analysis for entropy detection.
"""

import ast
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.engine.cognitive")

# Known web3 libraries that indicate crypto-related entropy.
_WEB3_LIBS = frozenset(("web3", "eth_account", "solcx", "brownie", "ape", "moralis"))


class PredictorAST(ast.NodeVisitor):
    """AST analysis for intent prediction and background error resolution."""

    __slots__ = ("complex_branches", "bare_excepts", "web3_entropy")

    def __init__(self) -> None:
        self.complex_branches = 0
        self.bare_excepts = 0
        self.web3_entropy = 0

    def visit_If(self, node: ast.If) -> None:
        self.complex_branches += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
            self.bare_excepts += 1
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] in _WEB3_LIBS:
                self.web3_entropy += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".")[0] in _WEB3_LIBS:
            self.web3_entropy += 1
        self.generic_visit(node)


def scan_file_entropy(file_path: Path) -> list[dict[str, Any]]:
    """Deep analysis for entropy detection (Ω₂)."""
    from cortex.utils.landauer import calculate_calcification

    findings = []
    try:
        content = file_path.read_text("utf-8")
        tree = ast.parse(content)
        predictor = PredictorAST()
        predictor.visit(tree)

        if predictor.web3_entropy > 0:
            findings.append({"type": "WEB3_ENTROPY", "count": predictor.web3_entropy})
        if predictor.bare_excepts > 0:
            findings.append({"type": "BARE_EXCEPT", "count": predictor.bare_excepts})
        if predictor.complex_branches > 10:
            findings.append({"type": "COMPLEX_BRANCHES", "count": predictor.complex_branches})

        res = calculate_calcification(file_path)
        if res and res["score"] > 50.0:
            findings.append({"type": "THERMO_ENTROPY", "score": res["score"]})
            for node in res.get("nodes", []):
                if node["is_parasite"]:
                    findings.append(
                        {"type": "THERMAL_PARASITE", "name": node["name"], "score": node["score"]}
                    )
    except (SyntaxError, OSError, UnicodeDecodeError) as e:
        logger.debug("scan_file_entropy skipped %s: %s", file_path, e)
    return findings
