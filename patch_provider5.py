import re

with open("scripts/moltbook_adversarial.py", "r") as f:
    code = f.read()

code = code.replace(
    'llm = LLMProvider(provider="anthropic")',
    'llm = LLMProvider(provider="openai")'
)

with open("scripts/moltbook_adversarial.py", "w") as f:
    f.write(code)

print("Patch applied.")
