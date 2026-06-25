import pytest
from legacy_research.engine.ingest.landauer_compression import LandauerCompressor

def test_landauer_ast_pruning_removes_docstrings():
    source = '''
"""
Module level docstring. Should be purged.
"""
def hello_world():
    """Function docstring. Should be purged."""
    return "Hello"

class SovereignAgent:
    """Class docstring. Purge."""
    pass
'''
    compressed = LandauerCompressor.apply_compression(source, modality="python_code")
    
    assert 'Module level docstring' not in compressed
    assert 'Function docstring' not in compressed
    assert 'Class docstring' not in compressed
    assert 'def hello_world():' in compressed
    assert 'return \'Hello\'' in compressed or 'return "Hello"' in compressed
    assert 'class SovereignAgent:' in compressed

def test_landauer_invalid_syntax_fallback():
    source = "def broken_code(:"
    compressed = LandauerCompressor.apply_compression(source, modality="python_code")
    assert compressed == source

def test_landauer_ast_pruning_removes_prints_and_logs():
    source = '''
import logging
logger = logging.getLogger(__name__)

def execute_logic():
    print("Debug info")
    logger.info("Starting execution")
    logging.warning("This is a warning")
    x = 42
    return x
'''
    compressed = LandauerCompressor.apply_compression(source, modality="python_code")
    
    assert 'print' not in compressed
    assert 'logger.info' not in compressed
    assert 'logging.warning' not in compressed
    assert 'x = 42' in compressed
    assert 'return x' in compressed

