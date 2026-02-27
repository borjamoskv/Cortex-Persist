import re


def fix_execute_fetchall(content):
    # Pattern: var = conn.execute(...).fetchall()
    # It might be multiline.
    pattern = r"(?P<var>\w+)\s*=\s*conn\.execute\((.*?)\)\.fetchall\(\)"

    def repl(m):
        return f"cursor = await conn.execute({m.group(2)})\n    {m.group('var')} = await cursor.fetchall()"

    return re.sub(pattern, repl, content, flags=re.DOTALL)


def fix_execute_fetchone(content):
    pattern = r"(?P<var>\w+)\s*=\s*conn\.execute\((.*?)\)\.fetchone\(\)"

    def repl(m):
        return f"cursor = await conn.execute({m.group(2)})\n    {m.group('var')} = await cursor.fetchone()"

    content = re.sub(pattern, repl, content, flags=re.DOTALL)

    # inline usage: r = conn.execute("...", (fid,)).fetchone()
    # if it's already caught by above, great.
    return content


def fix_execute(content):
    # Just conn.execute -> await conn.execute
    pattern = r"conn\.execute\("
    return re.sub(pattern, "await conn.execute(", content)


def fix_all(filename):
    with open(filename, "r") as f:
        content = f.read()

    content = fix_execute_fetchall(content)
    content = fix_execute_fetchone(content)

    # then fix any remaining conn.execute -> await conn.execute
    content = re.sub(r"(?<!await )conn\.execute\(", "await conn.execute(", content)

    # fix conn.commit() -> await conn.commit()
    content = re.sub(r"(?<!await )conn\.commit\(", "await conn.commit(", content)

    with open(filename, "w") as f:
        f.write(content)


fix_all("dedup.py")
fix_all("merge_errors.py")
fix_all("staleness.py")
fix_all("lateral.py")
