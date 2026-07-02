"""
[C5-REAL] Test Suite for Asymmetric ZK Compiler
"""

import pytest
from babylon60.extensions.zk_compiler.core import AsymmetricZKCompiler


def test_simd_hash_gkr():
    compiler = AsymmetricZKCompiler()
    simd_circuit = "def parallel_hash(data): return [hash(x) for x in data]"
    res = compiler.compile_circuit("SIMD_Hash", simd_circuit)
    assert "GKR" in res["applied_invariants"]
    assert "GKRDataParallel" in res["optimized_source"]


def test_ivc_rollup_nova():
    compiler = AsymmetricZKCompiler()
    loop_circuit = (
        "def ivc_step(state): \n  for i in range(100): state = step(state)\n  return state"
    )
    res = compiler.compile_circuit("IVC_Rollup", loop_circuit)
    assert "Nova" in res["applied_invariants"]
    assert "NovaFoldingScheme" in res["optimized_source"]


def test_ram_lookup_logup():
    compiler = AsymmetricZKCompiler()
    lookup_circuit = "def ram_read(memory, ptr): return memory[ptr]"
    res = compiler.compile_circuit("ZK_VM_RAM", lookup_circuit)
    assert "LogUp" in res["applied_invariants"]
    assert "LogUpLookup" in res["optimized_source"]


def test_curve_cycle_recursion():
    compiler = AsymmetricZKCompiler()
    recursion_circuit = "def ivc_verify(proof, vk): return verify_proof(proof, vk)"
    res = compiler.compile_circuit("Recursive_SNARK", recursion_circuit)
    assert "CurveCycle" in res["applied_invariants"]
    assert "CurveCycleRecursion" in res["optimized_source"]


def test_bridge_consensus_folding():
    compiler = AsymmetricZKCompiler()
    bridge_consensus_circuit = "def check_light_client(headers): return verify_headers(headers)"
    res = compiler.compile_circuit("ZK_Bridge_Consensus", bridge_consensus_circuit)
    assert "ConsensusProofFolding" in res["applied_invariants"]
    assert "ConsensusProofFolding" in res["optimized_source"]


def test_bls_batch_verification():
    compiler = AsymmetricZKCompiler()
    bridge_sig_circuit = (
        "def check_validators(sigs, pubkeys, msg): return verify_bls_signatures(sigs, pubkeys, msg)"
    )
    res = compiler.compile_circuit("ZK_Bridge_BLS_Batch", bridge_sig_circuit)
    assert "BLSBatching" in res["applied_invariants"]
    assert "BLSBatchVerification" in res["optimized_source"]


def test_lasso_lookup_alu():
    compiler = AsymmetricZKCompiler()
    lasso_circuit = "def cpu_alu(a, b): return (a ^ b) & (a | b)"
    res = compiler.compile_circuit("ZKVM_ALU_Jolt", lasso_circuit)
    assert "LassoLookup" in res["applied_invariants"]
    assert "LassoLookup" in res["optimized_source"]
