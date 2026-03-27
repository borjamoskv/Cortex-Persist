import os
from typing import Any

import openai
from agents import Agent, Runner

# Constants
DEFAULT_MODEL = "gpt-5.4"  # As requested by user

audit_agent = Agent(
    name="byzantine_auditor",
    instructions=(
        "You are a CORTEX Sovereign Auditor. Your goal is to detect structural anomalies, "
        "Byzantine faults, and cognitive drift in the decision ledger. "
        "Analyze the provided transaction log. Look for: "
        "1. Inconsistent confidence levels given the content complexity."
        "2. Suspicious source patterns (e.g. unauthorized agents)."
        "3. Semantic drift between related decisions."
        "Emit a structured report with an anomaly score (0-100) and specific risk vectors."
    ),
    model=DEFAULT_MODEL,
)

async def run_byzantine_audit(records: list[dict[str, Any]], api_key: str | None = None) -> dict[str, Any]:
    """
    Runs a GPT-5.4 based audit on a set of ledger records.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"error": "Missing OPENAI_API_KEY", "score": 0, "vectors": []}

    client = openai.AsyncOpenAI(api_key=key)
    
    # Prepare logs for the agent
    log_summary = "\n".join([
        f"ID: {r.get('id')} | Source: {r.get('source')} | Confidence: {r.get('confidence')} | Content: {r.get('content')}"
        for r in records
    ])
    
    prompt = f"Analyze the following CORTEX ledger records for Byzantine anomalies:\n\n{log_summary}"
    
    try:
        result = await Runner.run(audit_agent, prompt, client=client)
        # Parse result (assuming structured text or JSON-like output from GPT-5.4)
        output = result.final_output
        return {
            "valid": "anomaly detected" not in output.lower(),
            "report": output,
            "score": 0, # Placeholder for parsed score
            "vectors": []
        }
    except Exception as e:
        return {"error": str(e), "score": 0, "vectors": []}
