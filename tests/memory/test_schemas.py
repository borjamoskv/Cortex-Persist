"""Tests for CORTEX v6 Schema Theory implementation."""
import pytest
from cortex.memory.schemas import SchemaEngine, MemorySchema

def test_schema_matching():
    engine = SchemaEngine()
    
    # Debug schema
    schema = engine.match_schema("I got a ValueError: list index out of range")
    assert schema is not None
    assert schema.name == "error_debugging"
    
    # ML schema
    schema = engine.match_schema("We need to optimize the training loss for this model")
    assert schema is not None
    assert schema.name == "machine_learning"
    
    # Frontend schema
    schema = engine.match_schema("The css is broken on this tailwind component")
    assert schema is not None
    assert schema.name == "frontend_ui"
    
    # No match
    schema = engine.match_schema("Just a normal conversation about philosophy")
    assert schema is None

def test_schema_encoding_bias():
    engine = SchemaEngine()
    schema = engine.match_schema("error:")
    assert schema is not None
    
    content = "This is a stacktrace error:\nTraceback (most recent call last):\nI am feeling Frustration! I hate this bug"
    focused_content = engine.apply_encoding_schema(schema, content)
    
    assert "[SCHEMA: error_debugging | FOCUS:" in focused_content
    assert "Stacktrace" in focused_content
    # "Frustration" is in ignore list, so that line should be filtered out
    assert "Frustration" not in focused_content
    assert "Traceback" in focused_content

def test_schema_retrieval_bias():
    engine = SchemaEngine()
    schema = engine.match_schema("I have a bug")
    assert schema is not None
    
    query = "Why did it fail?"
    biased_query = engine.apply_retrieval_schema(schema, query)
    
    assert biased_query.startswith("Why did it fail?")
    assert "error resolution" in biased_query
    assert "bug fix" in biased_query
