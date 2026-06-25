import pytest

from legacy_research.engine.oracle.ast_signer import generate_ast_signature

def test_generate_ast_signature_deterministic():
    code_1 = '''
def example(a, b):
    """This is a docstring."""
    return a + b
'''
    
    code_2 = '''
def example(a, b):
    return a + b
'''

    code_3 = '''
def example(a, b):
    # This is a comment
    return a + b
'''

    sig_1 = generate_ast_signature(code_1)
    sig_2 = generate_ast_signature(code_2)
    sig_3 = generate_ast_signature(code_3)

    assert sig_1.startswith("ast_sha3_256:")
    assert sig_1 == sig_2 == sig_3

def test_generate_ast_signature_raw_fallback():
    not_python_code = "This is not python code. {[]}"
    sig = generate_ast_signature(not_python_code)
    
    assert sig.startswith("raw_sha3_256:")
