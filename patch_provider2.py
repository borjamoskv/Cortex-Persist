
with open("scripts/moltbook_adversarial.py") as f:
    code = f.read()

code = code.replace(
    'llm = LLMProvider(provider="google")',
    'llm = LLMProvider(provider="gemini")'
)

with open("scripts/moltbook_adversarial.py", "w") as f:
    f.write(code)

print("Patch applied.")
