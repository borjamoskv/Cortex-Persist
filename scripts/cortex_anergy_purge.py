# [C5-REAL] Exergy-Maximized
"""
cat_id: cortex-anergy-purge
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import os
import shutil
import re
from pathlib import Path

# C5-REAL Anergy Purge Engine
# Thermodynamically quarantines purely narrative files

workspace_root = Path("/Users/borjafernandezangulo/30_CORTEX")
quarantine_dir = workspace_root / "docs" / "archive" / "narrative_quarantine"
quarantine_dir.mkdir(parents=True, exist_ok=True)

target_dirs = [
    workspace_root / "docs",
    workspace_root / "cortex" / "agents" / "ontology"
]

hype_keywords = [
    r"singularity", r"ouroboros", r"god[- ]mode", r"sovereign", r"exergy", r"anergy", 
    r"dissipative structure", r"apex", r"byzantine", r"bft", r"epistemic", r"containment",
    r"mitosis", r"swarm", r"legion", r"omega", r"c5-real", r"c4-sim", r"physical runtime",
    r"thermodynamic", r"entropy", r"landauer", r"autopoiesis", r"demiurge", r"cl4r1t4s",
    r"noir", r"quantum", r"forensic", r"isomorphism", r"apopto", r"centuria", r"destiny",
    r"supreme", r"immortal", r"cosmic", r"cybernetic", r"transversal", r"hypervisor"
]

# Files we must NEVER touch
sacred_files = [
    "AGENTS.md", "GEMINI.md", "README.md", "README.es.md", "README.zh.md", 
    "SECURITY.md", "CHANGELOG.md", "CONTRIBUTING.md", "MILESTONES.md",
    "ROADMAP.md", "CODE_OF_CONDUCT.md"
]

purged_files = []

def calculate_anergy_score(text):
    text_lower = text.lower()
    score = 0
    for kw in hype_keywords:
        score += len(re.findall(kw, text_lower))
    
    # Structural density check (code blocks, yaml, json, lists)
    code_blocks = len(re.findall(r"```[\s\S]*?```", text))
    yaml_blocks = len(re.findall(r"```yaml[\s\S]*?```", text))
    
    # If there are structural blocks, it reduces the anergy score
    score -= (code_blocks * 5)
    score -= (yaml_blocks * 10)
    
    return score

def scan_and_purge():
    for tdir in target_dirs:
        if not tdir.exists():
            continue
            
        for filepath in tdir.rglob("*.md"):
            # Skip if already in archive or quarantine
            if "archive" in str(filepath) or "narrative_quarantine" in str(filepath):
                continue
                
            if filepath.name in sacred_files:
                continue
                
            try:
                content = filepath.read_text(encoding="utf-8")
                anergy_score = calculate_anergy_score(content)
                
                # If score > 10 and no significant code structures, quarantine it
                if anergy_score >= 10:
                    dest = quarantine_dir / filepath.name
                    # If filename conflict, append hash
                    if dest.exists():
                        dest = quarantine_dir / f"{filepath.stem}_dupe{filepath.suffix}"
                    
                    shutil.move(str(filepath), str(dest))
                    purged_files.append(str(filepath.relative_to(workspace_root)))
            except Exception as e:
                pass

scan_and_purge()

with open(workspace_root / "purge_report.json", "w") as f:
    import json
    json.dump({"purged_count": len(purged_files), "files": purged_files}, f, indent=2)

print(f"Purged {len(purged_files)} high-anergy narrative files into quarantine.")
