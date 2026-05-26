import os
import sys
import json

def pass_func():
    return True

def simple_func(a):
    if a > 0:
        if a > 1:
            if a > 2:
                if a > 3:
                    return True
    return False

def medium_func(a):
    if a == 1: pass
    elif a == 2: pass
    elif a == 3: pass
    elif a == 4: pass
    elif a == 5: pass
    elif a == 6: pass
    elif a == 7: pass
    elif a == 8: pass
    elif a == 9: pass
    elif a == 10: pass
    elif a == 11: pass
    elif a == 12: pass
    elif a == 13: pass
    elif a == 14: pass
    return a

def fail_func(a):
    if a == 1: pass
    if a == 2: pass
    if a == 3: pass
    if a == 4: pass
    if a == 5: pass
    if a == 6: pass
    if a == 7: pass
    if a == 8: pass
    if a == 9: pass
    if a == 10: pass
    if a == 11: pass
    if a == 12: pass
    if a == 13: pass
    if a == 14: pass
    if a == 15: pass
    if a == 16: pass
    if a == 17: pass
    if a == 18: pass
    if a == 19: pass
    if a == 20: pass
    if a == 21: pass
    if a == 22: pass
    if a == 23: pass
    if a == 24: pass

if __name__ == "__main__":
    # Create a temporary file to audit
    test_file = "temp_audit_test.py"
    with open(test_file, "w") as f:
        f.write('''
def pass_func():
    return True

def simple_func(a):
    if a > 0:
        if a > 1:
            if a > 2:
                if a > 3:
                    return True
    return False

def medium_func(a):
    if a == 1: pass
    elif a == 2: pass
    elif a == 3: pass
    elif a == 4: pass
    elif a == 5: pass
    elif a == 6: pass
    elif a == 7: pass
    elif a == 8: pass
    elif a == 9: pass
    elif a == 10: pass
    elif a == 11: pass
    elif a == 12: pass
    elif a == 13: pass
    elif a == 14: pass
    return a

def fail_func(a):
    if a == 1: pass
    if a == 2: pass
    if a == 3: pass
    if a == 4: pass
    if a == 5: pass
    if a == 6: pass
    if a == 7: pass
    if a == 8: pass
    if a == 9: pass
    if a == 10: pass
    if a == 11: pass
    if a == 12: pass
    if a == 13: pass
    if a == 14: pass
    if a == 15: pass
    if a == 16: pass
    if a == 17: pass
    if a == 18: pass
    if a == 19: pass
    if a == 20: pass
    if a == 21: pass
    if a == 22: pass
    if a == 23: pass
    if a == 24: pass
''')

    # Import MirrorAuditor from cortex-core/mirror_audit.py
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cortex-core')))
    from mirror_audit import MirrorAuditor

    auditor = MirrorAuditor(test_file)
    if auditor.audit():
        report = auditor.report()
        findings = report["findings"]

        complexity_findings = [f for f in findings if f["type"] == "CYCLOMATIC_COMPLEXITY"]

        # Verify medium_func
        medium = next((f for f in complexity_findings if f["function"] == "medium_func"), None)
        assert medium is not None, "medium_func should have a complexity finding"
        assert medium["complexity"] == 15, f"medium_func complexity should be 15, got {medium['complexity']}"
        assert medium["status"] == "WARN", "medium_func status should be WARN"

        # Verify fail_func
        fail = next((f for f in complexity_findings if f["function"] == "fail_func"), None)
        assert fail is not None, "fail_func should have a complexity finding"
        assert fail["complexity"] == 25, f"fail_func complexity should be 25, got {fail['complexity']}"
        assert fail["status"] == "FAIL", "fail_func status should be FAIL"

        # Verify pass_func and simple_func are not in findings
        assert not any(f["function"] == "pass_func" for f in complexity_findings), "pass_func should not be in findings"
        assert not any(f["function"] == "simple_func" for f in complexity_findings), "simple_func should not be in findings"

        print("✅ Cyclomatic complexity tests passed!")
        os.remove(test_file)
    else:
        print("❌ Audit failed")
        os.remove(test_file)
        sys.exit(1)
