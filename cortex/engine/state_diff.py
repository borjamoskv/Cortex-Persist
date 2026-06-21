# [C5-REAL] Exergy-Maximized
"""
State Diff Engine for CORTEX Audit System.
Computes deep differences between JSON-serializable state representations
to generate JSON Patch format deltas. Reversible and hashable.
"""

import json
import hashlib
from typing import Any, Dict, List

# Basic recursive diff implementation for JSON patch
def generate_json_patch(prev_state: Dict[str, Any], new_state: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
    patches = []
    
    # Check for removed or modified keys
    for key in prev_state:
        current_path = f"{path}/{key}"
        if key not in new_state:
            patches.append({"op": "remove", "path": current_path, "old_value": prev_state[key]})
        else:
            old_val = prev_state[key]
            new_val = new_state[key]
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                patches.extend(generate_json_patch(old_val, new_val, current_path))
            elif old_val != new_val:
                patches.append({"op": "replace", "path": current_path, "value": new_val, "old_value": old_val})
                
    # Check for added keys
    for key in new_state:
        if key not in prev_state:
            current_path = f"{path}/{key}"
            patches.append({"op": "add", "path": current_path, "value": new_state[key]})
            
    return patches

def apply_patch(state: Dict[str, Any], patches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Applies a json patch to a state dictionary."""
    import copy
    new_state = copy.deepcopy(state)
    for patch in patches:
        keys = patch["path"].strip("/").split("/")
        target = new_state
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        last_key = keys[-1]
        op = patch["op"]
        
        if op == "add" or op == "replace":
            target[last_key] = patch["value"]
        elif op == "remove":
            if last_key in target:
                del target[last_key]
                
    return new_state

def reverse_patch(patches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reverses a patch sequence (Saga compensation)."""
    reversed_patches = []
    for patch in reversed(patches):
        if patch["op"] == "add":
            reversed_patches.append({"op": "remove", "path": patch["path"], "old_value": patch["value"]})
        elif patch["op"] == "remove":
            reversed_patches.append({"op": "add", "path": patch["path"], "value": patch["old_value"]})
        elif patch["op"] == "replace":
            reversed_patches.append({"op": "replace", "path": patch["path"], "value": patch["old_value"], "old_value": patch["value"]})
    return reversed_patches

class StateDiffEngine:
    @staticmethod
    def compute_diff(prev_state: Dict[str, Any], new_state: Dict[str, Any]) -> str:
        """Returns JSON serialized patch."""
        patches = generate_json_patch(prev_state, new_state)
        # canonical representation
        return json.dumps(patches, sort_keys=True, separators=(',', ':'))
        
    @staticmethod
    def hash_diff(diff_json: str) -> str:
        """Returns SHA3-256 hash of the diff."""
        m = hashlib.sha3_256()
        m.update(diff_json.encode('utf-8'))
        return m.hexdigest()
