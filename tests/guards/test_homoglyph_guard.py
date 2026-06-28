import pytest

from cortex.guards.homoglyph_guard import AntiHomoglyphGuard


def test_homoglyph_guard_clean_code():
    guard = AntiHomoglyphGuard(block_mode=True)
    code = """
def my_function(a, b):
    class MyClass:
        pass
    x = a + b
    return x
"""
    assert guard.check_code(code) is True


def test_homoglyph_guard_catches_cyrillic_a():
    guard = AntiHomoglyphGuard(block_mode=True)
    # The 'a' in 'fаke' is CYRILLIC SMALL LETTER A (U+0430)
    code = """
def fаke_function():
    pass
"""
    with pytest.raises(ValueError, match="HOMOGLYPH_ATTACK"):
        guard.check_code(code)


def test_homoglyph_guard_catches_greek_class():
    guard = AntiHomoglyphGuard(block_mode=True)
    # The 'B' in 'Βeta' is GREEK CAPITAL LETTER BETA (U+0392)
    code = """
class ΒetaClass:
    pass
"""
    with pytest.raises(ValueError, match="HOMOGLYPH_ATTACK"):
        guard.check_code(code)


def test_homoglyph_guard_catches_variable():
    guard = AntiHomoglyphGuard(block_mode=True)
    # The 'e' in 'tеst' is CYRILLIC SMALL LETTER IE (U+0435)
    code = """
def test_func():
    tеst = 123
    return tеst
"""
    with pytest.raises(ValueError, match="HOMOGLYPH_ATTACK"):
        guard.check_code(code)


def test_homoglyph_guard_non_blocking_mode():
    guard = AntiHomoglyphGuard(block_mode=False)
    # The 'a' in 'fаke' is CYRILLIC SMALL LETTER A (U+0430)
    code = """
def fаke_function():
    pass
"""
    # Should return False instead of raising ValueError
    assert guard.check_code(code) is False


def test_homoglyph_guard_skips_invalid_syntax():
    guard = AntiHomoglyphGuard(block_mode=True)
    code = "def fаke_function(:"  # syntax error
    assert guard.check_code(code) is True


def test_vector1_homoglyph_attack_rejected():
    from cortex.guards.homoglyph_guard import cassandra_validate_identifiers, SecurityViolation
    import ast

    # Cyrillic 'е' U+0435 in 'lеa_omega_purge'
    code = """
def lеa_omega_purge():
    pass
"""
    tree = ast.parse(code)
    with pytest.raises(SecurityViolation, match="HOMOGLYPH_ATTACK"):
        cassandra_validate_identifiers(tree)


def test_vector1_clean_ascii_accepted():
    from cortex.guards.homoglyph_guard import cassandra_validate_identifiers
    import ast

    code = """
def lea_omega_purge():
    x = 100
    return x
"""
    tree = ast.parse(code)
    cassandra_validate_identifiers(tree)  # Should pass without raising
