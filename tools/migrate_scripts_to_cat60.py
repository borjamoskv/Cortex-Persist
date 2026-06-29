# [C5-REAL] Exergy-Maximized
"""
cat_id: migrate-scripts-to-cat60
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import re
from pathlib import Path
import yaml

def migrate_python_script(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
        
        # Check if there is already a docstring header
        pattern = re.compile(r'^(?:#[^\n]*\n)*\s*"""(.*?)"""', re.DOTALL)
        match = pattern.match(content)
        
        existing_yaml = {}
        prefix_comments = ""
        body_part = content
        
        if match:
            # We already have a docstring block
            full_match_text = match.group(0)
            docstring = match.group(1).strip()
            
            # Extract yaml block from docstring
            meta_lines = []
            for line in docstring.splitlines():
                stripped = line.strip()
                if not stripped or ":" not in stripped:
                    break
                meta_lines.append(line)
            
            yaml_content = "\n".join(meta_lines)
            try:
                existing_yaml = yaml.safe_load(yaml_content) or {}
            except Exception:
                existing_yaml = {}
                
            body_part = content[len(full_match_text):]
            
            prefix_match = re.match(r'^(?:#[^\n]*\n)*', full_match_text)
            if prefix_match:
                prefix_comments = prefix_match.group(0)
                
        else:
            # No docstring at all. Keep existing prefix comments
            prefix_match = re.match(r'^(?:#[^\n]*\n)*', content)
            if prefix_match:
                prefix_comments = prefix_match.group(0)
                body_part = content[len(prefix_comments):]
                
        if not existing_yaml or not isinstance(existing_yaml, dict):
            existing_yaml = {}
            
        # Build CAT-60 metadata
        cat_metadata = {
            "cat_id": existing_yaml.get("cat_id") or path.stem.replace('_', '-'),
            "cat_type": existing_yaml.get("cat_type") or "script",
            "version": existing_yaml.get("version") or "1.0.0",
            "reality_level": existing_yaml.get("reality_level") or "C5-REAL",
            "owner": existing_yaml.get("owner") or "borjamoskv",
            "exergy_tier": existing_yaml.get("exergy_tier") or "P2",
        }
        
        for k, v in existing_yaml.items():
            if k not in cat_metadata:
                cat_metadata[k] = v
                
        new_yaml_block = yaml.dump(cat_metadata, default_flow_style=False, sort_keys=False).strip()
        
        if "# [C5-REAL]" not in prefix_comments:
            prefix_comments = "# [C5-REAL] Exergy-Maximized\n" + prefix_comments
            
        new_docstring = f'"""\n{new_yaml_block}\n"""\n'
        
        if not body_part.startswith('\n'):
            new_docstring += '\n'
            
        new_content = f"{prefix_comments}{new_docstring}{body_part}"
        
        path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error migrating {path.name}: {e}")
        return False

def main():
    workspace_root = Path(__file__).parent.parent.resolve()
    
    # We only run it on scripts/. tools/ is already verified.
    scripts_dirs = [workspace_root / "scripts"]
    
    migrated_count = 0
    for s_dir in scripts_dirs:
        if s_dir.exists():
            print(f"Migrating scripts in: {s_dir.relative_to(workspace_root)}")
            for file in sorted(s_dir.glob("*.py")):
                if migrate_python_script(file):
                    migrated_count += 1
                    print(f"  🟢 {file.name} -> Migrated")
                    
    print(f"\nSuccessfully migrated {migrated_count} scripts to CAT-60 standard.")

if __name__ == "__main__":
    main()
