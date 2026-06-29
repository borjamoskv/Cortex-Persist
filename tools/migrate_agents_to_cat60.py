# [C5-REAL] Exergy-Maximized
"""
cat_id: "migrate-agents-to-cat60"
cat_type: "script"
version: "1.0.0"
reality_level: "C5-REAL"
owner: "borjamoskv"
exergy_tier: "P2"
"""

from pathlib import Path

import yaml


def migrate_agent_file(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if not data or not isinstance(data, dict):
            return False
            
        existing_metadata = data.get("metadata", {})
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}
            
        # Build CAT-60 metadata
        metadata = {
            "cat_id": existing_metadata.get("cat_id") or path.stem,
            "cat_type": "agent",
            "version": existing_metadata.get("version") or "1.0.0",
            "reality_level": existing_metadata.get("reality_level") or "C5-REAL",
            "owner": existing_metadata.get("owner") or "borjamoskv",
            "exergy_tier": existing_metadata.get("exergy_tier") or "P1"
        }
        
        # Merge other metadata keys
        for k, v in existing_metadata.items():
            if k not in metadata:
                metadata[k] = v
                
        # Reconstruct the agent dict with metadata at the top
        new_data = {"metadata": metadata}
        for k, v in data.items():
            if k != "metadata":
                new_data[k] = v
                
        new_content = yaml.dump(new_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error migrating {path.name}: {e}")
        return False

def main():
    workspace_root = Path(__file__).parent.parent.resolve()
    agents_dir = workspace_root / "babylon60" / "extensions" / "agents" / "definitions"
    
    if not agents_dir.exists():
        print("Definitions directory not found.")
        return
        
    migrated_count = 0
    for file in sorted(agents_dir.glob("*.yaml")):
        if migrate_agent_file(file):
            migrated_count += 1
            print(f"  🟢 {file.name} -> Migrated")
            
    print(f"\nSuccessfully migrated {migrated_count} agents to CAT-60 standard.")

if __name__ == "__main__":
    main()
