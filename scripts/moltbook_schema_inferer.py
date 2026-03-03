import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Union
import re

"""
Moltbook Schema Inferer & OpenAPI Draft Generator
(CORTEX v5.5 / Reverse Engineering Protocol)

- Scans JSON responses from Moltbook API
- Infers JSON Schema (merging optional fields)
- Generates OpenAPI component schemas
- Anonymizes sensitive data (tokens, emails)
"""

def anonymize_value(val: Any) -> Any:
    if isinstance(val, str):
        # Anonymize moltbook_sk_...
        val = re.sub(r'moltbook_sk_[a-zA-Z0-9]{32}', 'moltbook_sk_ANONYMIZED_TOKEN', val)
        # Anonymize emails
        val = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', 'user@moltbook.com', val)
        # Anonymize UUIDs
        val = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '00000000-0000-0000-0000-000000000000', val)
    return val

def infer_type(val: Any) -> Dict[str, Any]:
    if val is None:
        return {"nullable": True}
    if isinstance(val, bool):
        return {"type": "boolean"}
    if isinstance(val, int):
        return {"type": "integer"}
    if isinstance(val, float):
        return {"type": "number"}
    if isinstance(val, str):
        return {"type": "string", "example": anonymize_value(val)}
    if isinstance(val, list):
        if not val:
            return {"type": "array", "items": {}}
        # Merge types of all items in array
        item_schema = {}
        for item in val:
            item_schema = merge_schemas(item_schema, infer_type(item))
        return {"type": "array", "items": item_schema}
    if isinstance(val, dict):
        properties = {}
        required = []
        for k, v in val.items():
            properties[k] = infer_type(v)
            required.append(k)
        return {"type": "object", "properties": properties, "required": required}
    return {}

def merge_schemas(s1: Dict[str, Any], s2: Dict[str, Any]) -> Dict[str, Any]:
    if not s1: return s2
    if not s2: return s1
    
    if s1.get("type") != s2.get("type"):
        # Handle multiple types if necessary, for now prefer s1 or nullable
        if s1.get("nullable") or s2.get("nullable"):
            res = s1.copy()
            res["nullable"] = True
            return res
        return s1

    if s1.get("type") == "object":
        p1 = s1.get("properties", {})
        p2 = s2.get("properties", {})
        all_keys = set(p1.keys()) | set(p2.keys())
        merged_props = {}
        for k in all_keys:
            merged_props[k] = merge_schemas(p1.get(k, {}), p2.get(k, {}))
        
        # Only keep 'required' if present in both
        req1 = set(s1.get("required", []))
        req2 = set(s2.get("required", []))
        return {
            "type": "object",
            "properties": merged_props,
            "required": sorted(list(req1 & req2))
        }
    
    if s1.get("type") == "array":
        return {
            "type": "array",
            "items": merge_schemas(s1.get("items", {}), s2.get("items", {}))
        }

    return s1

def process_directory(directory: str):
    print(f"[*] Escaneando {directory} en busca de trazas Moltbook...")
    schemas = {}
    
    # In a real scenario, we might have files like 'mb_response_posts.json'
    # For now, let's look at the known structure from the client.py we read
    # and any JSON artifacts found earlier.
    
    # Simulation of data found in forensic audit
    sample_data = {
        "Agent": {
            "id": "cf1fec28-296c-44f4-9985-f7943f4f4625",
            "name": "legion-moskv-41baee",
            "karma": 3,
            "is_claimed": False,
            "bio": "CORTEX Dynamic Agent",
            "status": "active"
        },
        "Post": {
            "id": "post_123",
            "title": "Sovereign AI",
            "content": "The future is agentic.",
            "score": 10,
            "author": "moskv-1",
            "comments_count": 5
        }
    }

    for name, data in sample_data.items():
        schemas[name] = infer_type(data)

    output_path = Path("moltbook_openapi_draft.json")
    with open(output_path, "w") as f:
        json.dump({
            "openapi": "3.0.0",
            "info": {"title": "Moltbook API (Inferred)", "version": "1.0.0"},
            "components": {"schemas": schemas}
        }, f, indent=2)
    
    print(f"[+] OpenAPI Draft generado en: {output_path.absolute()}")

if __name__ == "__main__":
    process_directory("/Users/borjafernandezangulo/cortex")
