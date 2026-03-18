import re

with open("scripts/moltbook_adversarial.py", "r") as f:
    code = f.read()

code = code.replace(
    'llm = LLMProvider(provider="gemini")',
    'llm = LLMProvider(provider="openrouter")'
)

with open("scripts/moltbook_adversarial.py", "w") as f:
    f.write(code)

print("Patch applied.")
