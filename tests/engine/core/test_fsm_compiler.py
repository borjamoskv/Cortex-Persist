import pytest

from babylon60.engine.core.fsm_regex import compile_regex, RegexParser, NFACompiler, build_dfa

# [C5-REAL] Exergy-Maximized


def test_ast_parsing_literal():
    parser = RegexParser("a")
    ast = parser.parse()
    assert ast.__class__.__name__ == "LiteralNode"
    assert ast.charset.matches("a")
    assert not ast.charset.matches("b")


def test_ast_parsing_concat():
    parser = RegexParser("ab")
    ast = parser.parse()
    assert ast.__class__.__name__ == "ConcatNode"


def test_ast_parsing_union():
    parser = RegexParser("a|b")
    ast = parser.parse()
    assert ast.__class__.__name__ == "UnionNode"


def test_dfa_evaluation_simple():
    vocab_chars = {"a", "b", "c"}
    dfa = compile_regex("ab*c", vocab_chars)

    assert dfa.matches("ac") is True
    assert dfa.matches("abc") is True
    assert dfa.matches("abbbc") is True
    assert dfa.matches("a") is False
    assert dfa.matches("bc") is False
    assert dfa.matches("ab") is False


def test_dfa_evaluation_union_plus():
    vocab_chars = {"a", "b", "c", "x", "y"}
    dfa = compile_regex("(a|b)+c", vocab_chars)

    assert dfa.matches("ac") is True
    assert dfa.matches("bc") is True
    assert dfa.matches("aabc") is True
    assert dfa.matches("babac") is True
    assert dfa.matches("c") is False
    assert dfa.matches("ab") is False


def test_dfa_evaluation_character_class():
    vocab_chars = {"1", "2", "3", "a"}
    dfa = compile_regex("[123]+a", vocab_chars)

    assert dfa.matches("1a") is True
    assert dfa.matches("123a") is True
    assert dfa.matches("22a") is True
    assert dfa.matches("a") is False
    assert dfa.matches("4a") is False  # 4 is not in vocab, would fail early in real integration


def test_dfa_evaluation_wildcard():
    vocab_chars = {"1", "2", "a", "b"}
    dfa = compile_regex("a.b", vocab_chars)

    assert dfa.matches("a1b") is True
    assert dfa.matches("a2b") is True
    assert dfa.matches("aab") is True
    assert dfa.matches("abb") is True
    assert dfa.matches("ab") is False
