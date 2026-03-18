import ast
from pathlib import Path
from typing import Any


class CortazarEngine:
    """
    Engine for detecting bureaucratic entropy (Famas) and
    proposing creative leaps (Cronopios).
    """

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)

    def detect_fama_bloat(self, file_path: str) -> dict[str, Any]:
        """
        Scans a file for 'Fama' characteristics:
        - Excessive boilerplate.
        - Deep inheritance (entropy increase).
        - Decorative comments without exergy.
        - High cyclomatic complexity.
        """
        results = {"is_fama": False, "entropy_score": 0.0, "complexity_score": 0, "reasons": []}

        try:
            content = Path(file_path).read_text()
            tree = ast.parse(content)

            # 1. Structural Complexity
            class_count = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_count += 1
                    if len(node.bases) > 3:
                        results["reasons"].append(f"Deep inheritance in {node.name}")
                        results["entropy_score"] += 0.3

                if isinstance(node, ast.If | ast.For | ast.While | ast.With | ast.Try):
                    results["complexity_score"] += 1

            # 2. Decorator/Comment Noise
            lines = content.splitlines()
            line_count = len(lines)
            comment_lines = sum(
                1 for line in lines if line.strip().startswith("#") or '"""' in line
            )
            comment_ratio = comment_lines / max(1, line_count)

            if comment_ratio > 0.4:
                results["reasons"].append(f"Excessive decorative noise ({comment_ratio:.2f})")
                results["entropy_score"] += 0.4

            # 3. God Object & Structural Fama
            if line_count > 600 and class_count < 2:
                results["reasons"].append("God Object (Monolithic Fama)")
                results["entropy_score"] += 0.6

            if results["complexity_score"] > 25:
                results["reasons"].append(
                    f"High cyclomatic complexity ({results['complexity_score']})"
                )
                results["entropy_score"] += 0.5

            if results["entropy_score"] > 0.7:
                results["is_fama"] = True

        except Exception as e:
            results["reasons"].append(f"Error parsing file: {e}")

        return results

    def hopscotch_leap(self, code_block: str) -> str:
        """
        Proposes a 'Rayuela' jump.
        Conceptual: Collapses multiple linear steps into a single bridge.
        """
        # Placeholder for AI-driven non-linear refactoring logic
        msg = "# [Ω-Cortázar Suggestion]: This block has high linear friction.\n"
        msg += "# Shift to a direct Memory Bridge or Axiom-based execution.\n"
        return f"{msg}{code_block}"

    def ludic_inquiry(self, component_name: str) -> list[str]:
        """
        Asks Socratic questions to expose hidden 'Fama' premises.
        """
        return [
            f"¿Hacia dónde se escapa la exergía de `{component_name}`?",
            f"Si `{component_name}` fuera un Cronopio, ¿cómo saltaría sobre su propia sombra?",
            f"¿Qué pasaría si borramos el 40% de `{component_name}` y solo dejamos el deseo?",
        ]


if __name__ == "__main__":
    # Internal test
    engine = CortazarEngine()
    print("Ω-Cortázar ready for inquiry.")
