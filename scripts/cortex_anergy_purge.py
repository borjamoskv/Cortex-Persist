# [C5-REAL] Exergy-Maximized
"""
cat_id: cortex-anergy-purge
cat_type: script
version: 1.1.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import json
import os
import re
import shutil
from pathlib import Path

# C5-REAL Anergy Purge Engine
# Thermodynamically quarantines purely narrative files and performs ledger apoptosis.

workspace_root = Path(__file__).resolve().parent.parent
# Fallback to current working directory if not structured
if not (workspace_root / "babylon60").exists():
    workspace_root = Path(os.getcwd())

quarantine_dir = workspace_root / "docs" / "archive" / "narrative_quarantine"
quarantine_dir.mkdir(parents=True, exist_ok=True)

target_dirs = [
    workspace_root / "docs",
    workspace_root / "babylon60" / "agents" / "ontology"
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
                
                # If score >= 10 and no significant code structures, quarantine it
                if anergy_score >= 10:
                    dest = quarantine_dir / filepath.name
                    # If filename conflict, append hash
                    if dest.exists():
                        dest = quarantine_dir / f"{filepath.stem}_dupe{filepath.suffix}"
                    
                    shutil.move(str(filepath), str(dest))
                    purged_files.append(str(filepath.relative_to(workspace_root)))
            except Exception:
                pass

async def perform_ledger_apoptosis():
    print("[C5-REAL] Iniciando purga termodinámica de Ledger (Apoptosis)...")
    try:
        from babylon60.audit.ledger import EnterpriseAuditLedger
        from babylon60.audit.ledger_compactor import compact_ledger
        from babylon60.database.core import connect_async_ctx
        
        db_path = str(workspace_root / "cortex_ledger.db")
        if not os.path.exists(db_path):
            print(f"[C5-REAL] Ledger database no existe en {db_path}. Omitiendo Apoptosis.")
            return None
            
        async with connect_async_ctx(db_path) as conn:
            ledger = EnterpriseAuditLedger(conn)
            # Compact if we have complete batches (compact all but the last one)
            result = await compact_ledger(conn, ledger, max_rows=1000, snapshot_dir=workspace_root / ".snapshots")
            print(f"[C5-REAL] Apoptosis de Ledger: {result}")
            return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    import sys
    # Add workspace to path to allow import
    sys.path.insert(0, str(workspace_root))
    
    # 1. Perform standard file purge
    scan_and_purge()
    
    # 2. Run ledger apoptosis
    import asyncio
    os.environ["CORTEX_TEST_ENV"] = "1"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        compaction_res = loop.run_until_complete(perform_ledger_apoptosis())
    finally:
        loop.close()
    
    # 3. Dump report
    report_path = workspace_root / "purge_report.json"
    report_data = {
        "purged_count": len(purged_files),
        "files": purged_files,
        "ledger_apoptosis": compaction_res
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
        
    print(f"Purged {len(purged_files)} high-anergy narrative files into quarantine.")
