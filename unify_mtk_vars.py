import sys

filepath = "cortex/engine/mtk_python.py"
with open(filepath, 'r') as f:
    content = f.read()

bad_code = """def set_ephemeral_token(token: str) -> None:
    mtk_ephemeral_token.set(token)

def clear_ephemeral_token() -> None:
    mtk_ephemeral_token.set(None)"""

good_code = """def set_ephemeral_token(token: str) -> None:
    mtk_ephemeral_token.set(token)
    from cortex.engine.mtk_sqlite_authorizer import mtk_active_token
    mtk_active_token.set(token)

def clear_ephemeral_token() -> None:
    mtk_ephemeral_token.set(None)
    from cortex.engine.mtk_sqlite_authorizer import mtk_active_token
    mtk_active_token.set(None)"""

if bad_code in content:
    content = content.replace(bad_code, good_code)
    with open(filepath, 'w') as f:
        f.write(content)
    print("Fixed cortex/engine/mtk_python.py")
else:
    print("Not found in cortex/engine/mtk_python.py")

filepath = "cortex/engine/mtk_python.py"
try:
    with open(filepath, 'r') as f:
        content = f.read()
    if bad_code in content:
        content = content.replace(bad_code, good_code)
        with open(filepath, 'w') as f:
            f.write(content)
        print("Fixed cortex/engine/mtk_python.py")
except FileNotFoundError:
    pass

