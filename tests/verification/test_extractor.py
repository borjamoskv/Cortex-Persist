import pytest

from cortex.verification.extractor import SMTModelExtractor, extract_constraints


def test_extract_constraints_syntax_error():
    code = "invalid python code"
    findings = extract_constraints(code)
    assert len(findings) == 1
    assert findings[0]["invariant_id"] == "SYNTAX"
    assert "Code parsing failed" in findings[0]["message"]


def test_extract_constraints_valid_code_no_violations():
    code = "x = 1\ny = x + 2\nprint(y)"
    findings = extract_constraints(code)
    assert len(findings) == 0


def test_smtmodelextractor_analyze_delete():
    code = "db.delete('table')"
    extractor = SMTModelExtractor(code)
    findings = extractor.analyze()
    assert len(findings) == 1
    assert findings[0]["invariant_id"] == "I2"
    assert "Prohibited method call: delete" in findings[0]["message"]


def test_smtmodelextractor_analyze_eval():
    code = "eval('1 + 1')"
    extractor = SMTModelExtractor(code)
    findings = extractor.analyze()
    assert len(findings) == 1
    assert findings[0]["invariant_id"] == "I7"
    assert "Prohibited use of 'eval'" in findings[0]["message"]


def test_smtmodelextractor_visit_for():
    code = "for i in range(10):\n  pass"
    extractor = SMTModelExtractor(code)
    findings = extractor.analyze()
    # Currently visit_For only logs debug and visits generic, no violation is added
    assert len(findings) == 0


def test_extract_constraints_helper_delete():
    code = "user.remove()"
    findings = extract_constraints(code)
    assert len(findings) == 1
    assert findings[0]["invariant_id"] == "I2"
    assert "Prohibited method call: remove" in findings[0]["message"]
