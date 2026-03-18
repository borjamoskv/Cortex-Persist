
with open("scripts/moltbook_adversarial.py") as f:
    code = f.read()

code = code.replace(
    'MoltbookClient(api_key="dummy")',
    'MoltbookClient()'
)

code = code.replace(
    '''    try:
        reg_result = await mb_client.register(
            name=agent_name, description="I propose highly controversial, advanced theorems."
        )
    except Exception as e:
        logger.error("[%s] Falla en registro: %s", agent_name, e)
        return None

    api_key = reg_result.get("agent", {}).get("api_key")
    if not api_key:
        return None

    mb_client = MoltbookClient(api_key=api_key)''',
    '''    # Skip registration, use default logged-in client'''
)

code = code.replace(
    '''    try:
        reg_result = await mb_client.register(
            name=agent_name, description="I systematically dismantle flawed theorems."
        )
    except Exception as e:
        logger.error("[%s] Falla en registro: %s", agent_name, e)
        return

    api_key = reg_result.get("agent", {}).get("api_key")
    if not api_key:
        return

    mb_client = MoltbookClient(api_key=api_key)''',
    '''    # Skip registration, use default logged-in client'''
)


with open("scripts/moltbook_adversarial.py", "w") as f:
    f.write(code)

print("Patch applied.")
