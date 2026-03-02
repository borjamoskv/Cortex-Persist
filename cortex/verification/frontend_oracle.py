"""
Ω₇ Zero-Latency UI Axiom Enforcer.
Evaluates Cognitive Complexity of JavaScript/TypeScript functions in frontend files.
"""

from __future__ import annotations

import re
from typing import Any


class FrontendOracle:
    """Heuristic logic to enforce CC < 5 on reactive UI listeners."""

    def __init__(self):
        self.max_complexity = 5

    def analyze_file(self, filepath: str) -> list[dict[str, Any]]:
        """Returns a list of violations for a given file."""
        violations = []
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return violations

        # Extract JS blocks from .html or use full content for .js/.ts
        if filepath.endswith(".html"):
            scripts = re.findall(
                r"<script.*?>\s*(.*?)\s*</script>", content, re.DOTALL | re.IGNORECASE
            )
            js_content = "\n".join(scripts)
        else:
            js_content = content

        # Find function blocks (heuristic). Regex isn't perfect but handles standard cases.
        # Matches: function name(...) {
        # or: const name = (...) => {
        function_pattern = re.compile(
            r"(?:function\s+(\w+)\s*\(.*?\)\s*\{)|"
            r"(?:(?:const|let|var)\s+(\w+)\s*=\s*\(.*?\)\s*=>\s*\{)",
            re.DOTALL,
        )

        for match in function_pattern.finditer(js_content):
            func_name = match.group(1) or match.group(2)
            if not func_name:
                continue

            # If it's a listener or handler (handleLiveUpdate, addEventListener context, etc.)
            if (
                "handle" in func_name.lower()
                or "listener" in func_name.lower()
                or "update" in func_name.lower()
            ):
                # Extract the body roughly (counting braces)
                start_idx = match.end()
                body = self._extract_block(js_content, start_idx - 1)
                complexity = self._calculate_complexity(body)

                if complexity >= self.max_complexity:
                    violations.append(
                        {
                            "file": filepath,
                            "function": func_name,
                            "complexity": complexity,
                            "threshold": self.max_complexity,
                        }
                    )
        return violations

    def _extract_block(self, text: str, start_index: int) -> str:
        """Extracts the block enclosed by curly braces starting at start_index."""
        open_braces = 0
        for i in range(start_index, len(text)):
            if text[i] == "{":
                open_braces += 1
            elif text[i] == "}":
                open_braces -= 1
                if open_braces == 0:
                    return text[start_index : i + 1]
        return text[start_index:]  # Fallback

    def _calculate_complexity(self, body: str) -> int:
        """Heuristic calculation of cognitive complexity."""
        complexity = 0
        # Branches
        complexity += len(re.findall(r"\bif\s*\(", body))
        complexity += len(re.findall(r"\belse\s+if\s*\(", body))
        complexity += len(re.findall(r"\bfor\s*\(", body))
        complexity += len(re.findall(r"\bwhile\s*\(", body))
        complexity += len(re.findall(r"\bcatch\s*\(", body))
        complexity += len(re.findall(r"\bswitch\s*\(", body))
        # Logical operators (often increment complexity)
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        complexity += len(re.findall(r"\?", body))  # ternaries
        return complexity
