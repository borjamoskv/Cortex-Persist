#!/usr/bin/env python3
"""
Test Hito 09: VSA Recursive Anchoring
"""
import hashlib
import json
from db import store_fact, load_vsa_tensor, vsa_xor, VSA_PARENT_LABEL

def test_vsa_recursion():
    print("--- TESTING HITO 09: RECURSIVE ANCHOR ---")
    
    # 1. Create Parent Fact
    p_content = "The core of CORTEX is Silicon Reason."
    p_meta = {"subject": "parent_fact"}
    p_res = store_fact("test_tenant", "test_script", p_content, p_meta)
    parent_id = p_res["id"]
    print(f"Parent Recorded: {parent_id}")
    
    # Manually save a dummy vector for the parent (normally the LLM bridge does this)
    dummy_vec = b"\x11" * 1250
    from native_paths import PROJECT_ROOT
    from pathlib import Path
    vsa_dir = PROJECT_ROOT / "data" / "vsa_memory"
    vsa_dir.mkdir(parents=True, exist_ok=True)
    (vsa_dir / f"cortex_default_{parent_id}.vsa").write_bytes(dummy_vec)
    
    # 2. Create Child Fact with parent_id
    c_content = "Kant-Omega is the enforcer of Silicon Reason."
    c_meta = {"subject": "child_fact", "parent_id": parent_id}
    c_res = store_fact("test_tenant", "test_script", c_content, c_meta)
    child_id = c_res["id"]
    print(f"Child Recorded with Anchor: {child_id}")
    
    # 3. Verify Anchored Vector
    # The child's vector should now be: Child_HV ^ (H_PARENT_LABEL ^ Parent_HV)
    # But for this test, store_fact assumes child_vector exists to anchor it.
    # Since we didn't save a child_vector first, vsa_recursive_anchor would fail if it can't load it.
    
    # Let's fix the test by providing the child vector first
    child_dummy = b"\x22" * 1250
    (vsa_dir / f"cortex_default_{child_id}.vsa").write_bytes(child_dummy)
    
    # RE-RUN Anchor
    from db import vsa_recursive_anchor
    vsa_recursive_anchor("cortex_default", child_id, parent_id)
    
    anchored_vec = load_vsa_tensor("cortex_default", child_id)
    
    # Mathematically: anchored_vec ^ child_dummy = (H_PARENT_LABEL ^ dummy_vec)
    reconstructed_link = vsa_xor(anchored_vec, child_dummy)
    expected_link = vsa_xor(VSA_PARENT_LABEL, dummy_vec)
    
    if reconstructed_link == expected_link:
        print("✅ SUCCESS: VSA Recursive Anchor Verified (Algebraic proof passed).")
    else:
        print("❌ FAILURE: VSA Algebra Mismatch.")

if __name__ == "__main__":
    test_vsa_recursion()
