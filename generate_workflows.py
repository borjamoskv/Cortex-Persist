import os
import glob
import yaml

skills_dir = os.path.expanduser('~/.gemini/antigravity/skills')
workflows_dir = os.path.expanduser('~/cortex/.agent/workflows')

skill_paths = glob.glob(os.path.join(skills_dir, '*/SKILL.md'))

for sp in skill_paths:
    skill_folder = os.path.basename(os.path.dirname(sp))
    
    # generate a workflow name
    # typically strip '-1' or '-omega' or use the full name
    wf_name = skill_folder
    if skill_folder.endswith('-1'):
        wf_name = skill_folder[:-2]
    
    wf_path = os.path.join(workflows_dir, f"{wf_name}.md")
    if not os.path.exists(wf_path):
        wf_path = os.path.join(workflows_dir, f"{skill_folder}.md")
        
    # Read the skill description from SKILL.md yaml frontmatter
    description = ""
    try:
        with open(sp, 'r') as f:
            content = f.read()
            if content.startswith('---'):
                parts = content.split('---')
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter and 'description' in frontmatter:
                        description = frontmatter['description']
    except Exception as e:
        print(f"Error reading {sp}: {e}")
        
    if not description:
        description = f"Execute the {skill_folder} skill protocol."
        
    workflow_content = f"""---
description: {description}
---

1. Read the full skill instructions:
   ```bash
   cat ~/.gemini/antigravity/skills/{skill_folder}/SKILL.md
   ```
// turbo

2. Follow the skill protocol exactly as documented in the SKILL.md file.
"""
    
    with open(os.path.join(workflows_dir, f"{skill_folder}.md"), 'w') as f:
        f.write(workflow_content)
    print(f"Generated workflow for {skill_folder} at {skill_folder}.md")

print("All missing workflows generated.")
