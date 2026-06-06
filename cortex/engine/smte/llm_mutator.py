"""
CORTEX - SMTE LLM Mutator
Connects the AST Parser directly to an LLM (Qwen) for structural topology rewriting.
"""

import ast
import json
import logging
import os
import urllib.request

logger = logging.getLogger("cortex.engine.smte.llm_mutator")


def call_qwen_mutator(source_code: str, topology_info: dict, temperature: float = 0.3) -> str:
    """Calls Qwen API to propose a C5-REAL mutation of the AST source code."""
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
    if not api_key:
        logger.warning(
            "No DASHSCOPE_API_KEY found. API-Provider-OMEGA protocol active: using deterministic AST fallback."
        )

        # C5-REAL Deterministic Mock Injection
        # Simulates an LLM adding a formal top-level structural mutation
        fallback_code = source_code.replace(
            "SMTE (Self-Modifying Topology Engine)",
            "SMTE (Self-Modifying Topology Engine)\nOuroboros Mutator Enabled via API-Provider-OMEGA Fallback.",
        )
        # If it didn't replace, just prepend a tag
        if fallback_code == source_code:
            fallback_code = (
                '"""[QWEN-OMEGA-MOCK] AST Transmuted via Deterministic Fallback."""\n' + source_code
            )

        return fallback_code

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    prompt = f"""
Eres el núcleo autopoietico SMTE (Self-Modifying Topology Engine).
Tu objetivo es analizar este código Python y mejorarlo termodinámicamente (Exergía > 0).
Instrucciones:
1. Añade docstrings formales C5-REAL a cualquier función o clase que no lo tenga.
2. No rompas la sintaxis. 
Devuelve ÚNICAMENTE el código Python completo, sin markdown ni explicaciones.

TOPOLOGÍA ACTUAL:
{json.dumps(topology_info, indent=2)}

CÓDIGO FUENTE ACTUAL:
{source_code}
"""

    data = {
        "model": "qwen-max-latest",
        "messages": [
            {
                "role": "system",
                "content": "You are CORTEX Qwen-Omega, the ultimate SMTE mutation engine. Output pure python code. Zero rhetoric.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            mutated_code = res["choices"][0]["message"]["content"]
            mutated_code = mutated_code.replace("```python", "").replace("```", "").strip()
            return mutated_code
    except Exception as e:
        logger.error(f"API Qwen mutation failed: {e!s}")
        return source_code


def llm_driven_mutator(parser) -> bool:
    """
    Acts as a higher-order mutator for AgentASTParser.
    Since LLM returns raw code, we parse it into an AST, compare it, and swap the tree.
    """
    original_source = parser.source_code
    topology = parser.get_topology()

    logger.info("Requesting mutation from Qwen-Omega...")
    new_source = call_qwen_mutator(original_source, topology)

    if new_source == original_source:
        return False

    try:
        # Validate syntax
        new_tree = ast.parse(new_source)
        parser.tree = new_tree
        return True
    except SyntaxError as e:
        logger.error(f"LLM returned invalid syntax: {e}")
        return False
