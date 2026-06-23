import pytest
from babylon60.engine.mutation_tester import MutationTester
import tempfile
import os

def test_mutation_tester():
    # Create a dummy Python file with tests
    dummy_code = """
def is_positive(n):
    return n > 0

def test_is_positive():
    assert is_positive(5) == True
    assert is_positive(-1) == False
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(dummy_code)
        temp_path = f.name

    try:
        tester = MutationTester(test_cmd=f"pytest {temp_path}")
        results = tester.mutate_and_test(temp_path, target_lines=[3]) # Mutating line 3
        
        assert results["mutants_created"] > 0
        assert results["mutants_killed"] > 0 or results["mutants_survived"] > 0
    finally:
        os.unlink(temp_path)
