# [C5-REAL] Exergy-Maximized
"""
cat_id: "validate-taxonomy"
cat_type: "script"
version: "1.0.0"
reality_level: "C5-REAL"
owner: "borjamoskv"
exergy_tier: "P2"
"""

import re
import sys
from pathlib import Path

import yaml


def check_yaml_agent(path: Path) -> tuple[bool, str]:
    """Verify if a YAML agent definition contains valid CAT-60 metadata."""
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return False, "Invalid YAML structure (not a dictionary)"
        
        metadata = data.get("metadata")
        if not metadata:
            return False, "Missing 'metadata' root key"
        
        required_keys = ["cat_id", "cat_type", "version", "reality_level", "owner", "exergy_tier"]
        for key in required_keys:
            if key not in metadata:
                return False, f"Missing required metadata field: {key}"
        
        if metadata.get("cat_type") != "agent":
            return False, f"Incorrect cat_type: expected 'agent', got '{metadata.get('cat_type')}'"
            
        return True, "Valid"
    except Exception as e:
        return False, f"Error parsing: {e}"

def check_markdown_workflow(path: Path) -> tuple[bool, str]:
    """Verify if a markdown workflow contains valid CAT-60 frontmatter."""
    try:
        content = path.read_text(encoding="utf-8")
        
        # Match frontmatter possibly preceded by comments
        pattern = re.compile(r"^(?:<!--.*?-->\s*)?---(.*?)---", re.DOTALL)
        match = pattern.match(content)
        if not match:
            return False, "Missing frontmatter delimiter"
        
        yaml_content = match.group(1)
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            return False, "Frontmatter is not a dictionary"
            
        required_keys = ["cat_id", "cat_type", "version", "reality_level", "owner", "exergy_tier"]
        for key in required_keys:
            if key not in data:
                return False, f"Missing required frontmatter field: {key}"
                
        if data.get("cat_type") not in ["workflow", "policy", "skill"]:
            return False, f"Incorrect cat_type: {data.get('cat_type')}"
            
        return True, "Valid"
    except Exception as e:
        return False, f"Error parsing: {e}"

def check_python_script(path: Path) -> tuple[bool, str]:
    """Verify if a Python script contains valid CAT-60 docstring metadata."""
    try:
        content = path.read_text(encoding="utf-8")
        # Extract first block docstring
        pattern = re.compile(r'^(?:#[^\n]*\n)*\s*"""(.*?)"""', re.DOTALL)
        match = pattern.match(content)
        if not match:
            return False, "Missing docstring header"
            
        docstring = match.group(1).strip()
        
        # Extract key-value block at the start of docstring
        meta_lines = []
        for line in docstring.splitlines():
            stripped = line.strip()
            if not stripped:
                break
            if ":" not in stripped:
                break
            meta_lines.append(line)
            
        yaml_content = "\n".join(meta_lines)
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            return False, "Docstring metadata is not a valid YAML dictionary"
            
        required_keys = ["cat_id", "cat_type", "version", "reality_level", "owner", "exergy_tier"]
        for key in required_keys:
            if key not in data:
                return False, f"Missing required metadata field: {key}"
                
        if data.get("cat_type") != "script":
            return False, f"Incorrect cat_type: expected 'script', got '{data.get('cat_type')}'"
            
        return True, "Valid"
    except Exception as e:
        return False, f"Error parsing: {e}"

def main() -> int:
    workspace_root = Path(__file__).parent.parent.resolve()
    
    # Target directories
    agents_dir = workspace_root / "babylon60" / "extensions" / "agents" / "definitions"
    workflows_dirs = [
        workspace_root / ".agents" / "workflows",
        workspace_root / ".agent" / "workflows"
    ]
    scripts_dirs = [
        workspace_root / "tools",
        workspace_root / "scripts"
    ]
    
    failed = False
    
    print("=== CAT-60 TAXONOMY AUDIT ===")
    
    # 1. Audit Agents
    if agents_dir.exists():
        print(f"\nScanning Agents in: {agents_dir.relative_to(workspace_root)}")
        for file in sorted(agents_dir.glob("*.yaml")):
            ok, reason = check_yaml_agent(file)
            status_char = "🟢" if ok else "🔴"
            print(f"  {status_char} {file.name} -> {reason}")
            if not ok:
                failed = True
                
    # 2. Audit Workflows
    for w_dir in workflows_dirs:
        if w_dir.exists():
            print(f"\nScanning Workflows in: {w_dir.relative_to(workspace_root)}")
            for file in sorted(w_dir.glob("*.md")):
                ok, reason = check_markdown_workflow(file)
                status_char = "🟢" if ok else "🔴"
                print(f"  {status_char} {file.name} -> {reason}")
                if not ok:
                    failed = True
                
    # 3. Audit Scripts
    for s_dir in scripts_dirs:
        if s_dir.exists():
            print(f"\nScanning Scripts in: {s_dir.relative_to(workspace_root)}")
            for file in sorted(s_dir.glob("*.py")):
                ok, reason = check_python_script(file)
                status_char = "🟢" if ok else "🔴"
                print(f"  {status_char} {file.name} -> {reason}")
                # Fail hard on any tool directory scripts (our controlled scripts)
                if not ok and s_dir.name == "tools":
                    failed = True
                
    if failed:
        print("\n❌ TAXONOMY VERIFICATION FAILED: Incompliant critical assets detected.")
        return 1
    
    print("\n🟢 TAXONOMY VERIFICATION PASSED: Scanned assets check completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
