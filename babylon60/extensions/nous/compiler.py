
import logging

logger = logging.getLogger(__name__)
"""
C5-REAL: NOUS-Lang AST Compiler for CORTEX
Transforms NOUS declarative intents into CORTEX Saga Guard ASTs.
"""

from typing import Any

from pydantic import BaseModel, Field


class NousIntent(BaseModel):
    name: str
    ensures: list[str] = Field(default_factory=list)
    preserves: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)


class CortexASTNode(BaseModel):
    action_type: str
    target: str
    constraints: dict[str, Any]
    dry_run_supported: bool = True


class NousCompiler:
    def __init__(self):
        # Base compiler engine logic. Future iter will link LLM-driven parsing.
        pass

    def parse(self, raw_nous_text: str) -> NousIntent:
        """
        Parses raw .nous file into structured Intent.
        """
        lines = [line.strip() for line in raw_nous_text.split("\n") if line.strip()]

        intent_name = "Unknown"
        ensures, preserves, requires = [], [], []

        for line in lines:
            if line.startswith("intent "):
                intent_name = line.split("intent ")[1].split("{")[0].strip()
            elif line.startswith("ensure "):
                ensures.append(line.replace("ensure ", "").strip())
            elif line.startswith("preserve "):
                preserves.append(line.replace("preserve ", "").strip())
            elif line.startswith("require "):
                requires.append(line.replace("require ", "").strip())

        return NousIntent(name=intent_name, ensures=ensures, preserves=preserves, requires=requires)

    def compile(self, intent: NousIntent) -> list[CortexASTNode]:
        """
        Compiles NOUS Intent into executable CORTEX AST Nodes.
        """
        nodes = []
        for ensure_stmt in intent.ensures:
            nodes.append(
                CortexASTNode(
                    action_type="migrate_schema",
                    target=ensure_stmt,
                    constraints={"preserves": intent.preserves, "requires": intent.requires},
                )
            )
        return nodes


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath) as f:
            content = f.read()

        compiler = NousCompiler()
        intent = compiler.parse(content)
        ast = compiler.compile(intent)

        logger.info(f"--- PARSED INTENT ---\n{intent.model_dump_json(indent=2)}")
        logger.info(f"\n--- COMPILED AST ---\n{[node.model_dump_json(indent=2) for node in ast]}")
    else:
        logger.info("Usage: python compiler.py <path_to_nous_file>")
