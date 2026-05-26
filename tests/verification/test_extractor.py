import pytest
from cortex.verification.extractor import extract_constraints, SMTModelExtractor


def test_extract_constraints_syntax_error():
    code = "def foo(:"
    findings = extract_constraints(code)
    assert len(findings) == 1
    assert findings[0]["invariant_id"] == "SYNTAX"
    assert "Code parsing failed" in findings[0]["message"]


def test_extract_constraints_prohibited_methods():
    code = """
def bad_func(db):
    db.delete('table')
    db.remove('item')
    db.drop_table('table')
"""
    findings = extract_constraints(code)
    assert len(findings) == 3
    assert all(f["invariant_id"] == "I2" for f in findings)
    assert findings[0]["message"] == "Prohibited method call: delete"
    assert findings[1]["message"] == "Prohibited method call: remove"
    assert findings[2]["message"] == "Prohibited method call: drop_table"


def test_extract_constraints_eval():
    code = """
def bad_eval(x):
    eval(x)
"""
    findings = extract_constraints(code)
    assert len(findings) == 1
    assert findings[0]["invariant_id"] == "I7"
    assert findings[0]["message"] == "Prohibited use of 'eval' prevents termination analysis."


def test_extract_constraints_for_loop():
    code = """
def loop_func(items):
    for item in items:
        pass
"""
    # The current implementation of visit_For doesn't add findings, just logs debug
    findings = extract_constraints(code)
    assert len(findings) == 0


def test_smt_model_extractor_direct():
    extractor = SMTModelExtractor("x = 1")
    findings = extractor.analyze()
    assert len(findings) == 0
