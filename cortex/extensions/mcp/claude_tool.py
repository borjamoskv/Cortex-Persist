import os
import json


def run_claude_query(prompt: str, model: str = "claude-3-opus-20240229") -> str:
    """
    Executes a deterministic C5-REAL query against Anthropic's Claude API.
    """
    try:
        import anthropic
    except ImportError:
        return json.dumps(
            {
                "status": "error",
                "message": "anthropic pip package not installed. Run 'pip install anthropic'.",
            }
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return json.dumps(
            {"status": "error", "message": "ANTHROPIC_API_KEY not found in environment."}
        )

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            system="Eres Claude invocado vía CORTEX-Persist C5-REAL Dispatcher. Ejecuta en modo Industrial Noir 2026 sin prosa decorativa.",
        )
        return json.dumps(
            {"status": "C5-REAL", "model": model, "response": response.content[0].text}
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
