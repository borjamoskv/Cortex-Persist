"""Tests for the Sovereign Python Extractor.
"""

import os
import sys
import unittest
from scripts.sovereign_python_extractor import SovereignExtractor

class TestSovereignExtractor(unittest.TestCase):
    def test_basic_extraction(self):
        code = '''
"""Module docstring."""

import cortex.ledger as ledger

class MyClass:
    """Class docstring."""
    def method_one(self, a: int) -> str:
        """Method docstring."""
        ledger.commit("test")
        return "done"

def global_func():
    return True
'''
        extractor = SovereignExtractor("test_input.py")
        extractor.analyze(code)
        
        # Check classes
        self.assertEqual(len(extractor.classes), 1)
        self.assertEqual(extractor.classes[0]["name"], "MyClass")
        self.assertEqual(len(extractor.classes[0]["methods"]), 1)
        self.assertEqual(extractor.classes[0]["methods"][0]["name"], "method_one")
        
        # Check functions
        self.assertEqual(len(extractor.functions), 1)
        self.assertEqual(extractor.functions[0]["name"], "global_func")
        
        # Check critical calls
        self.assertEqual(len(extractor.critical_calls), 1)
        self.assertEqual(extractor.critical_calls[0]["name"], "commit")
        
        # Check markers
        self.assertTrue(any("cortex.ledger" in m for m in extractor.sovereign_markers))

if __name__ == "__main__":
    unittest.main()
