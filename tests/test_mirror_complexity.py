import unittest
import os
import tempfile
import json
import sys

# Add the directory containing mirror_audit.py to sys.path
sys.path.append(os.path.join(os.getcwd(), "cortex-core"))
from mirror_audit import MirrorAuditor


class TestMirrorAuditComplexity(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def create_test_file(self, content):
        path = os.path.join(self.test_dir.name, "test_file.py")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_pass_complexity(self):
        code = """
def simple_function(x):
    if x > 0:
        return True
    return False
"""
        path = self.create_test_file(code)
        auditor = MirrorAuditor(path)
        auditor.audit()
        report = auditor.report()

        self.assertEqual(len(report["complexity_metrics"]), 1)
        self.assertEqual(report["complexity_metrics"][0]["complexity"], 2)
        self.assertEqual(report["complexity_metrics"][0]["status"], "pass")

    def test_warn_complexity(self):
        # Complexity 11: 1 (base) + 10 branches
        code = """
def medium_function(x):
    if x == 1: pass
    if x == 2: pass
    if x == 3: pass
    if x == 4: pass
    if x == 5: pass
    if x == 6: pass
    if x == 7: pass
    if x == 8: pass
    if x == 9: pass
    if x == 10: pass
"""
        path = self.create_test_file(code)
        auditor = MirrorAuditor(path)
        auditor.audit()
        report = auditor.report()

        self.assertEqual(report["complexity_metrics"][0]["complexity"], 11)
        self.assertEqual(report["complexity_metrics"][0]["status"], "warn")

    def test_fail_complexity(self):
        # Complexity 21: 1 (base) + 20 branches
        code = "def complex_function(x):\n" + "\n".join(
            [f"    if x == {i}: pass" for i in range(20)]
        )
        path = self.create_test_file(code)
        auditor = MirrorAuditor(path)
        auditor.audit()
        report = auditor.report()

        self.assertEqual(report["complexity_metrics"][0]["complexity"], 21)
        self.assertEqual(report["complexity_metrics"][0]["status"], "fail")

    def test_module_level_analysis(self):
        code = """
def simple():
    return 1

def complex_one(x):
    if x == 1: pass
    if x == 2: pass
    if x == 3: pass
    if x == 4: pass
    if x == 5: pass
    if x == 6: pass
    if x == 7: pass
    if x == 8: pass
    if x == 9: pass
    if x == 10: pass
    if x == 11: pass
    if x == 12: pass
    if x == 13: pass
    if x == 14: pass
    if x == 15: pass
    if x == 16: pass
    if x == 17: pass
    if x == 18: pass
    if x == 19: pass
    if x == 20: pass
"""
        path = self.create_test_file(code)
        auditor = MirrorAuditor(path)
        auditor.audit()
        report = auditor.report()

        metrics = {m["function"]: m for m in report["complexity_metrics"]}
        self.assertEqual(metrics["simple"]["status"], "pass")
        self.assertEqual(metrics["complex_one"]["status"], "fail")
        self.assertEqual(metrics["complex_one"]["complexity"], 21)


if __name__ == "__main__":
    unittest.main()
