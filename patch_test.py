import re

with open("tests/test_virgo_guard.py") as f:
    content = f.read()

# find test_virgo_agent_valid_fallback_signature
new_content = content.replace(
    "async def test_virgo_agent_valid_fallback_signature(",
    "async def test_virgo_agent_valid_fallback_signature(\n    import asyncio\n    asyncio.get_running_loop().call_later(2, lambda: __import__('run_test_with_debug').dump())\n",
)
new_content = re.sub(
    r"async def test_virgo_agent_valid_fallback_signature\([^)]*\):",
    "async def test_virgo_agent_valid_fallback_signature(engine_unlocked):\n    import asyncio\n    asyncio.get_running_loop().call_later(5, lambda: __import__('run_test_with_debug').dump())",
    content,
)

with open("tests/test_virgo_guard.py", "w") as f:
    f.write(new_content)
