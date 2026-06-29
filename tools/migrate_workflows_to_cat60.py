# [C5-REAL] Exergy-Maximized
"""
cat_id: "migrate-workflows-to-cat60"
cat_type: "script"
version: "1.0.0"
reality_level: "C5-REAL"
owner: "borjamoskv"
exergy_tier: "P2"
"""

import re
from pathlib import Path

import yaml


def migrate_markdown_file(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
        
        # Check for frontmatter
        # We handle files starting with frontmatter, or having comments before it
        pattern = re.compile(r"^(<!--.*?-->\s*)?---(.*?)---(.*)$", re.DOTALL)
        match = pattern.match(content)
        
        comment_part = ""
        body_part = content
        existing_yaml = {}
        
        if match:
            comment_part = match.group(1) or ""
            yaml_block = match.group(2)
            body_part = match.group(3)
            try:
                existing_yaml = yaml.safe_load(yaml_block) or {}
            except Exception:
                existing_yaml = {}
        
        # Build CAT-60 frontmatter
        cat_metadata = {
            "cat_id": existing_yaml.get("cat_id") or path.stem,
            "cat_type": existing_yaml.get("cat_type") or "workflow",
            "version": existing_yaml.get("version") or "1.0.0",
            "reality_level": existing_yaml.get("reality_level") or "C5-REAL",
            "owner": existing_yaml.get("owner") or "borjamoskv",
            "exergy_tier": existing_yaml.get("exergy_tier") or "P1",
        }
        
        # Keep other existing keys (like description)
        for k, v in existing_yaml.items():
            if k not in cat_metadata:
                cat_metadata[k] = v
                
        # Format the new content
        new_yaml_block = yaml.dump(cat_metadata, default_flow_style=False, sort_keys=False).strip()
        new_content = f"{comment_part}---\n{new_yaml_block}\n---\n{body_part}"
        
        path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error migrating {path.name}: {e}")
        return False

def main():
    workspace_root = Path(__file__).parent.parent.resolve()
    
    workflows_dirs = [
        workspace_root / ".agents" / "workflows",
        workspace_root / ".agent" / "workflows"
    ]
    
    migrated_count = 0
    for w_dir in workflows_dirs:
        if w_dir.exists():
            print(f"Migrating workflows in: {w_dir.relative_to(workspace_root)}")
            for file in w_dir.glob("*.md"):
                if migrate_markdown_file(file):
                    migrated_count += 1
                    print(f"  🟢 {file.name} -> Migrated")
                    
    print(f"\nSuccessfully migrated {migrated_count} workflows to CAT-60 standard.")

if __name__ == "__main__":
    main()
