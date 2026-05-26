import os
import re
import json

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent

SKILLS_DIR = str(Path.home() / ".gemini" / "antigravity" / "skills")
TARGET_DIR = str(PROJECT_ROOT / "cortex-core" / "compiled_skills")


def parse_skill_markdown(filepath):
    """Parse skill markdown and extract metadata and body."""
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    # Parse YAML frontmatter using basic regex
    regex = r'^---\s*\n(.*?)\n---\s*\n(.*)'
    frontmatter_match = re.match(regex, content, re.DOTALL)

    metadata = {}
    body = content

    if frontmatter_match:
        yaml_content = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        # Simple Name and Description parse
        for line in yaml_content.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                metadata[key.strip()] = val.strip().strip("'\"")

    return metadata, body


def compile_to_python(skill_folder, metadata, body):
    """Compile skill instructions into a Python object template."""
    safe_name = skill_folder.replace('-', '_').replace('.', '_').lower()
    class_name = "".join(x.capitalize() for x in safe_name.split('_'))
    class_name += "Skill"

    description = metadata.get('description', 'No description provided')
    encoded_body = json.dumps(body)  # To escape quotes securely

    template = f"""\"\"\"
CORTEX JIT Compiled Skill: {skill_folder}
Description: {description}
\"\"\"
import json
import logging

class {class_name}:
    def __init__(self):
        self.name = "{skill_folder}"
        self.description = {json.dumps(description)}
        self.instructions = {encoded_body}

    def get_system_prompt(self):
        return self.instructions

    def execute(self, payload: dict) -> dict:
        \"\"\"
        O(1) execution wrapper.
        In Cycle 1 (MCP), this will bind via API to Cortex Swarm.
        \"\"\"
        logging.info(f"[{{self.name}}] Executing logic...")
        # A wrapper returning the prompt context for Frontier Models
        # or executing underlying local hooks if defined.
        return {{
            "status": "success",
            "skill": self.name,
            "injected_knowledge_tokens": len(self.instructions.split()),
            "yield_impact": "O(1) Execution",
            "extracted_payload": payload
        }}
"""
    return safe_name, template


def main():
    """Main entry point for skill compilation."""
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)

    compiled_count = 0
    init_exports = []

    for folder in os.listdir(SKILLS_DIR):
        skill_path = os.path.join(SKILLS_DIR, folder)
        if not os.path.isdir(skill_path):
            continue

        md_file = os.path.join(skill_path, "SKILL.md")
        if not os.path.exists(md_file):
            continue

        parsed = parse_skill_markdown(md_file)
        if not parsed:
            continue

        metadata, body = parsed
        safe_name, py_code = compile_to_python(folder, metadata, body)

        out_file = os.path.join(TARGET_DIR, f"{safe_name}.py")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(py_code)

        init_exports.append(safe_name)
        compiled_count += 1
        print(f"Compiled: {folder} -> {safe_name}.py")

    # Generate __init__.py registry
    with open(os.path.join(TARGET_DIR, "__init__.py"), "w") as f:
        f.write("# CORTEX COMPILED SKILLS REGISTRY\n")
        f.write("COMPILED_SKILLS = [\n")
        for ex in init_exports:
            f.write(f"    '{ex}',\n")
        f.write("]\n")

    msg = (
        f"\n[CORTEX JIT] Successfully compiled {compiled_count} "
        "markdown skills to Python objects."
    )
    print(msg)


def run_compiler():
    """Run the JIT Skill Compiler."""
    main()


if __name__ == "__main__":
    main()
