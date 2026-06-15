def test_bridge_compilation(bridge_compiler):
    exp = {"route": "cmd", "params": ["a", "b"]}
    act = {"route": "cmd", "params": ["a"]}
    artifact = bridge_compiler.compile_bridge("agent1", exp, act)
    assert artifact.bridge_id is not None
    assert "kwargs.get(\"b\", None)" in artifact.adapter_code
    assert "kwargs.get(\"a\")" in artifact.adapter_code

def test_bridge_cache_hit(bridge_compiler):
    exp = {"route": "cmd", "params": ["a", "b"]}
    act = {"route": "cmd", "params": ["a"]}
    artifact1 = bridge_compiler.compile_bridge("agent1", exp, act)
    artifact2 = bridge_compiler.compile_bridge("agent1", exp, act)
    assert artifact1 is artifact2  # Identity check for O(1) cache hit

def test_bridge_cache_invalidation(bridge_compiler):
    exp = {"route": "cmd", "params": ["a", "b"]}
    act = {"route": "cmd", "params": ["a"]}
    artifact1 = bridge_compiler.compile_bridge("agent1", exp, act)
    
    bridge_compiler.invalidate_cache()
    assert not bridge_compiler.cache
    
    artifact2 = bridge_compiler.compile_bridge("agent1", exp, act)
    # The new artifact might have the same bridge_id, but it is a newly instantiated object
    assert artifact1 is not artifact2

def test_bridge_execute_compiled_code(bridge_compiler):
    exp = {"route": "cmd", "params": ["a", "b"]}
    act = {"route": "cmd", "params": ["a"]}
    artifact = bridge_compiler.compile_bridge("agent1", exp, act)
    
    # Execute adapter code in a local namespace
    local_ns = {}
    exec(artifact.adapter_code, {}, local_ns)
    bridge_adapter = local_ns["bridge_adapter"]
    
    called_with = {}
    def mock_fn(a, b=None):
        called_with["a"] = a
        called_with["b"] = b
        return "success"
        
    res = bridge_adapter(mock_fn, a=10, b=20, extra=30)
    assert res == "success"
    assert called_with == {"a": 10, "b": 20}

def test_bridge_generation_no_params(bridge_compiler):
    artifact = bridge_compiler.compile_bridge("agent1", {}, {})
    local_ns = {}
    exec(artifact.adapter_code, {}, local_ns)
    bridge_adapter = local_ns["bridge_adapter"]
    
    called = []
    def mock_fn():
        called.append(True)
        return "ok"
    
    res = bridge_adapter(mock_fn, x=1)
    assert res == "ok"
    assert called == [True]

