# [C5-REAL] Exergy-Maximized
import re

# Allows only alphanumeric characters and underscores, starting with a letter or underscore, up to 64 chars.
_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}\Z")


def is_safe_identifier(name: str) -> bool:
    """Return True if name is a safe SQL identifier, else False."""
    return bool(_SAFE_IDENTIFIER.match(name))


def validate_sql_identifier(name: str) -> str:
    """Raise ValueError if name is not a safe SQL identifier."""
    if not is_safe_identifier(name):
        raise ValueError(f"Unsafe SQL identifier rejected: {name!r}")
    return name


def quote_identifier(name: str) -> str:
    """Quote a SQL identifier, raising ValueError if it is unsafe."""
    validate_sql_identifier(name)
    return f'"{name}"'
