import re

with open("tests/test_integration_engine.py") as f:
    code = f.read()

if "from cortex.database.core import causal_write" not in code:
    code = code.replace("import pytest", "import pytest\nfrom cortex.database.core import causal_write")

code = re.sub(
    r'(await conn\.execute\(\s*"INSERT INTO facts.*?\)[\s\n]+await conn\.commit\(\))',
    r'with causal_write(conn):\n                \1',
    code,
    flags=re.DOTALL
)

# And for the connection pool stability test
code = re.sub(
    r'(await conn\.execute\(\s*"INSERT INTO facts.*?\)[\s\n]+)',
    r'with causal_write(conn):\n                \1',
    code,
    flags=re.DOTALL
)

with open("tests/test_integration_engine.py", "w") as f:
    f.write(code)

print("Tests aggressively patched to respect causal_write boundary.")
