import pytest
from cortex_rs import EpistemicGraph, EpistemicNode, EpistemicStatus

def test_edg_node_creation():
    node = EpistemicNode("auth_logic_v1", 0.95)
    assert node.id == "auth_logic_v1"
    assert node.status == EpistemicStatus.Accepted
    assert node.confidence == 0.95

def test_edg_graph_dependencies():
    graph = EpistemicGraph()
    
    # Create nodes
    # Node A: Database Schema
    node_a = EpistemicNode("schema_v1", 1.0)
    # Node B: Auth Service
    node_b = EpistemicNode("auth_svc", 0.9)
    # Node C: Web UI
    node_c = EpistemicNode("web_ui", 0.9)
    
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)
    
    # A supports B
    graph.add_dependency("schema_v1", "auth_svc")
    # B supports C
    graph.add_dependency("auth_svc", "web_ui")
    
    # Verify status
    assert graph.get_node_status("web_ui") == EpistemicStatus.Accepted
    
    # Now invalidate the root schema
    # Blast radius should hit B and C
    affected = graph.invalidate_node("schema_v1")
    
    assert "schema_v1" in affected
    assert "auth_svc" in affected
    assert "web_ui" in affected
    
    # Check that status propagates properly
    assert graph.get_node_status("schema_v1") == EpistemicStatus.Invalid
    assert graph.get_node_status("auth_svc") == EpistemicStatus.Invalid
    assert graph.get_node_status("web_ui") == EpistemicStatus.Invalid
