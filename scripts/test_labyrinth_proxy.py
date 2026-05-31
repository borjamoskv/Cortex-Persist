import os
import sys
import time
from openai import OpenAI
from httpx import Client

# ---------------------------------------------------------
# C5-REAL: Labyrinth Proxy Integration Test
# ---------------------------------------------------------
# Validates the thermodynamic purge middleware layer.

PROXY_URL = "http://localhost:8000/api/llm-proxy/v1"


def output_msg(msg: str):
    sys.stdout.write(msg + "\n")


def test_labyrinth_routing():
    output_msg("Status: C5-REAL")
    output_msg(f"Target: {PROXY_URL}")
    output_msg("Action: Initiating test payload through Labyrinth Middleware...\n")

    try:
        client = OpenAI(
            base_url=PROXY_URL,
            api_key=os.environ.get("OPENAI_API_KEY", "sk-labyrinth-dummy-key"),
            http_client=Client(timeout=10.0),
        )

        start_time = time.time()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are subjected to a thermodynamic exergy filter. Speak concisely.",
                },
                {"role": "user", "content": "Output exactly one word: 'ACK'"},
            ],
            temperature=0.0,
        )

        elapsed = time.time() - start_time

        output_msg("Claim: Proxy routing successful.")
        output_msg(
            f"Proof: {{ Response: [{response.choices[0].message.content.strip()}], Latency: [{elapsed:.2f}s], Confidence: [C5-REAL] }}"
        )
        sys.exit(0)

    except Exception as e:
        output_msg("Claim: Proxy connection or filter rejected payload.")
        output_msg(f"Proof: {{ Error: [{e!s}], Confidence: [C5-REAL] }}")
        sys.exit(1)


if __name__ == "__main__":
    test_labyrinth_routing()
