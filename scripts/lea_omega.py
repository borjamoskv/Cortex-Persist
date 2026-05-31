#!/usr/bin/env python3
import os
import sys
import re
import shutil
from datetime import datetime

# LEA-Ω: Loose End Annihilator & Token Hygiene Enforcer
# Designed under C5-REAL parameters with zero-dependencies.

HOME = os.path.expanduser("~")
WORKFLOWS_PATH_1 = os.path.join(HOME, ".agents", "workflows")
WORKFLOWS_PATH_2 = os.path.join(HOME, "COLD_STORAGE", "cortex-config", "workflows")
SKILLS_PATH_1 = os.path.join(HOME, ".gemini", "config", "skills")
SKILLS_PATH_2 = os.path.join(HOME, ".gemini", "antigravity", "skills")

LIMIT_WORKFLOWS = 30
LIMIT_SKILLS = 45
MAX_DESCRIPTION_LEN = 100

def get_files_by_mtime(directory, extension=".md"):
    if not os.path.isdir(directory):
        return []
    files = []
    for f in os.listdir(directory):
        fpath = os.path.join(directory, f)
        if os.path.isfile(fpath) and f.endswith(extension):
            files.append((fpath, os.path.getmtime(fpath)))
    # Sort descending by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in files]

def get_skills_directories(skills_parent):
    if not os.path.isdir(skills_parent):
        return []
    dirs = []
    for name in os.listdir(skills_parent):
        dpath = os.path.join(skills_parent, name)
        if os.path.isdir(dpath) and name != "_archived":
            skill_md = os.path.join(dpath, "SKILL.md")
            if os.path.isfile(skill_md):
                dirs.append((dpath, os.path.getmtime(skill_md)))
    # Sort descending by modification time (newest first)
    dirs.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in dirs]

def parse_frontmatter(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        # Simple frontmatter parser
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            return {}, content
        
        yaml_content = match.group(1)
        body = content[match.end():]
        
        metadata = {}
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                metadata[key.strip()] = val.strip().strip('"').strip("'")
        return metadata, body
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
        return {}, ""

def write_with_frontmatter(filepath, metadata, body):
    frontmatter = "---\n"
    for k, v in metadata.items():
        # Handle description format
        if k == "description" and len(v) > MAX_DESCRIPTION_LEN:
            v = v[:MAX_DESCRIPTION_LEN-3] + "..."
        frontmatter += f"{k}: {v}\n"
    frontmatter += "---\n"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + body)

def clean_file(filepath):
    try:
        metadata, body = parse_frontmatter(filepath)
        
        # 1. Strip trailing whitespaces
        cleaned_body = "\n".join([line.rstrip() for line in body.split("\n")])
        
        # 2. Compress description if exceeds threshold
        changed = False
        if "description" in metadata and len(metadata["description"]) > MAX_DESCRIPTION_LEN:
            metadata["description"] = metadata["description"][:MAX_DESCRIPTION_LEN-3] + "..."
            changed = True
            
        # Re-write file
        write_with_frontmatter(filepath, metadata, cleaned_body)
        return True, changed
    except Exception as e:
        print(f"Error cleaning {filepath}: {e}", file=sys.stderr)
        return False, False

def run_lea(audit_only=True):
    print("=== LEA-Ω: LOOSE END ANNIHILATOR ===")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Mode: {'AUDIT' if audit_only else 'PURGE & OPTIMIZE'}")
    
    total_freed_bytes = 0
    anomalies = []
    optimizations = 0
    
    # --- 1. Workflow Audit ---
    print("\n--- Scanning Workflows ---")
    workflows = []
    for d in [WORKFLOWS_PATH_1, WORKFLOWS_PATH_2]:
        if os.path.exists(d):
            workflows.extend(get_files_by_mtime(d))
            
    # Remove duplicates from multiple sources based on basename
    seen_basenames = set()
    unique_workflows = []
    for w in workflows:
        base = os.path.basename(w)
        if base not in seen_basenames:
            seen_basenames.add(base)
            unique_workflows.append(w)
            
    print(f"Total Unique Workflows: {len(unique_workflows)}")
    
    # 2. Archive exceeded workflows
    if len(unique_workflows) > LIMIT_WORKFLOWS:
        excess = unique_workflows[LIMIT_WORKFLOWS:]
        print(f"WARNING: Workflows count ({len(unique_workflows)}) exceeds threshold ({LIMIT_WORKFLOWS}).")
        for w in excess:
            anomalies.append(f"Excess Workflow: {os.path.basename(w)}")
            if not audit_only:
                archive_dir = os.path.join(os.path.dirname(w), "_archived")
                os.makedirs(archive_dir, exist_ok=True)
                dest = os.path.join(archive_dir, os.path.basename(w))
                shutil.move(w, dest)
                print(f"[ARCHIVED] -> {dest}")
                total_freed_bytes += os.path.getsize(dest)
                optimizations += 1
    
    # Clean active workflows
    for w in unique_workflows[:LIMIT_WORKFLOWS]:
        if os.path.exists(w):
            meta, body = parse_frontmatter(w)
            desc = meta.get("description", "")
            if len(desc) > MAX_DESCRIPTION_LEN:
                anomalies.append(f"Workflow '{os.path.basename(w)}' description too long ({len(desc)} chars)")
                if not audit_only:
                    success, changed = clean_file(w)
                    if success:
                        print(f"[COMPRESSED] frontmatter in {w}")
                        optimizations += 1
            
            # Trailing whitespace check
            has_trailing = False
            for line in body.split("\n"):
                if line != line.rstrip():
                    has_trailing = True
                    break
            
            if has_trailing:
                anomalies.append(f"Workflow '{os.path.basename(w)}' has trailing whitespaces")
                if not audit_only:
                    success, changed = clean_file(w)
                    if success:
                        print(f"[STRIPPED] trailing whitespaces in {w}")
                        optimizations += 1

    # --- 2. Skills Audit ---
    print("\n--- Scanning Skills ---")
    skills = []
    for d in [SKILLS_PATH_1, SKILLS_PATH_2]:
        if os.path.exists(d):
            skills.extend(get_skills_directories(d))
            
    seen_skill_names = set()
    unique_skills = []
    for s in skills:
        name = os.path.basename(s)
        if name not in seen_skill_names:
            seen_skill_names.add(name)
            unique_skills.append(s)
            
    print(f"Total Unique Skills: {len(unique_skills)}")
    
    # Archive exceeded skills
    if len(unique_skills) > LIMIT_SKILLS:
        excess = unique_skills[LIMIT_SKILLS:]
        print(f"WARNING: Skills count ({len(unique_skills)}) exceeds threshold ({LIMIT_SKILLS}).")
        for s in excess:
            anomalies.append(f"Excess Skill: {os.path.basename(s)}")
            if not audit_only:
                archive_dir = os.path.join(os.path.dirname(s), "_archived")
                os.makedirs(archive_dir, exist_ok=True)
                dest = os.path.join(archive_dir, os.path.basename(s))
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.move(s, dest)
                print(f"[ARCHIVED] -> {dest}")
                optimizations += 1
                
    # Clean active skills
    for s in unique_skills[:LIMIT_SKILLS]:
        skill_md = os.path.join(s, "SKILL.md")
        if os.path.exists(skill_md):
            meta, body = parse_frontmatter(skill_md)
            desc = meta.get("description", "")
            if len(desc) > MAX_DESCRIPTION_LEN:
                anomalies.append(f"Skill '{os.path.basename(s)}' description too long ({len(desc)} chars)")
                if not audit_only:
                    success, changed = clean_file(skill_md)
                    if success:
                        print(f"[COMPRESSED] frontmatter in {skill_md}")
                        optimizations += 1
            
            # Trailing whitespace check
            has_trailing = False
            for line in body.split("\n"):
                if line != line.rstrip():
                    has_trailing = True
                    break
            
            if has_trailing:
                anomalies.append(f"Skill '{os.path.basename(s)}' has trailing whitespaces")
                if not audit_only:
                    success, changed = clean_file(skill_md)
                    if success:
                        print(f"[STRIPPED] trailing whitespaces in {skill_md}")
                        optimizations += 1

    print("\n--- AUDIT RESULTS ---")
    print(f"Total Anomalies Found: {len(anomalies)}")
    for a in anomalies:
        print(f" - [!] {a}")
        
    print(f"\nTotal Optimizations Applied: {optimizations}")
    if not audit_only:
        print(f"Total Exergy Reclaimed: {total_freed_bytes} bytes")
        
    return len(anomalies)

if __name__ == "__main__":
    audit = True
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        audit = False
    run_lea(audit_only=audit)
