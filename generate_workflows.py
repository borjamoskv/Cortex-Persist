import yaml
from pathlib import Path

SKILLS_DIR = Path("~/.gemini/antigravity/skills").expanduser()
WORKFLOWS_DIR = Path("~/cortex/.agent/workflows").expanduser()


def extract_description(skill_path: Path) -> str:
    """Extract description from YAML frontmatter."""
    try:
        content = skill_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                return frontmatter.get("description", "")
    except Exception as e:
        print(f"Error reading {skill_path}: {e}")
    return ""


def generate_workflow_content(skill_name: str, description: str) -> str:
    return f"""---
description: {description}
---

1. Read the full skill instructions:
   ```bash
   cat ~/.gemini/antigravity/skills/{skill_name}/SKILL.md
   ```
// turbo

2. Follow the skill protocol exactly as documented in the SKILL.md file.
"""


def main():
    if not SKILLS_DIR.exists():
        print(f"Skills directory not found: {SKILLS_DIR}")
        return

    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    for sp in SKILLS_DIR.glob("*/SKILL.md"):
        skill_name = sp.parent.name
        description = extract_description(sp) or f"Execute the {skill_name} skill protocol."

        target_path = WORKFLOWS_DIR / f"{skill_name}.md"
        target_path.write_text(generate_workflow_content(skill_name, description), encoding="utf-8")
        print(f"Generated workflow for {skill_name} at {target_path}")


if __name__ == "__main__":
    main()
