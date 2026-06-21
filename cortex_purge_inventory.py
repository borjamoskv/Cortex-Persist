import os
import shutil
import yaml
import time
from pathlib import Path

# Config
DRY_RUN = False

# Paths
BASE_DIR = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist")
ANTI_GRAVITY_DIR = BASE_DIR / "ANTI_GRAVITY"
INVENTORY_FILE = ANTI_GRAVITY_DIR / "inventory.yaml"

# Target directories to scan
SOURCE_DIRS = [
    BASE_DIR / "scripts",
    BASE_DIR / "experiments",
    BASE_DIR / ".agent" / "workflows",
    BASE_DIR / ".agents" / "workflows",
    BASE_DIR / "skills"
]

# Capabilities
CAPABILITIES = {
    "memory": ["memory", "cortex", "ledger", "persist", "state", "context", "store", "db", "sql"],
    "research": ["research", "search", "web", "scrape", "autodidact", "browser", "explore"],
    "creation": ["music", "visual", "image", "nft", "generator", "synth", "art", "create"],
    "automation": ["workflow", "runner", "cron", "daemon", "auto", "pipeline", "sync", "mac_control", "swarm", "agent"],
    "security": ["wallet", "guard", "audit", "forensic", "security", "rbac", "zero_debt", "taint", "crypto"],
    "observability": ["metrics", "radar", "telemetry", "dashboard", "log", "observe", "diagnose", "health"],
    "deployment": ["deploy", "init", "setup", "boot", "build", "docker", "manifest", "release"]
}

def determine_capability(filename, content=""):
    text = (filename + " " + content).lower()
    for cap, keywords in CAPABILITIES.items():
        if any(kw in text for kw in keywords):
            return cap
    return "unknown" # Mejorado como pidió el Operador

def determine_yield_score(filepath):
    # Heuristic based on file size, modification time, and name
    try:
        stat = filepath.stat()
        age_days = (time.time() - stat.st_mtime) / (24 * 3600)
        size = stat.st_size
    except:
        age_days = 100
        size = 0
    name = filepath.name.lower()
    
    score = 5 # default
    
    if age_days < 7:
        score += 3
    elif age_days > 30:
        score -= 2
        
    if "test" in name or "demo" in name or "bench" in name:
        score -= 2
    if "master" in name or "core" in name or "engine" in name:
        score += 3
        
    return max(1, min(10, score))

def determine_target_dir(score, capability):
    if score >= 8:
        return ANTI_GRAVITY_DIR / "01_ACTIVE" / capability
    elif score >= 4:
        return ANTI_GRAVITY_DIR / "04_ARCHIVE" / "yield_4_7"
    else:
        return ANTI_GRAVITY_DIR / "05_GRAVEYARD" / "yield_low"

inventory = {"capabilities": {cap: [] for cap in list(CAPABILITIES.keys()) + ["unknown"]}, "artifacts": []}

# Setup target folders
for cap in list(CAPABILITIES.keys()) + ["unknown"]:
    (ANTI_GRAVITY_DIR / "01_ACTIVE" / cap).mkdir(parents=True, exist_ok=True)
    (ANTI_GRAVITY_DIR / "02_SYSTEMS" / cap).mkdir(parents=True, exist_ok=True)
    
(ANTI_GRAVITY_DIR / "04_ARCHIVE" / "yield_4_7").mkdir(parents=True, exist_ok=True)
(ANTI_GRAVITY_DIR / "05_GRAVEYARD" / "yield_low").mkdir(parents=True, exist_ok=True)

artifact_id_counter = 1

for src_dir in SOURCE_DIRS:
    if not src_dir.exists():
        continue
    for root, _, files in os.walk(src_dir):
        if "__pycache__" in root or ".archive" in root:
            continue
        for file in files:
            if file.startswith(".") or file.endswith(".pyc"):
                continue
                
            filepath = Path(root) / file
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read(1000)
            except:
                content = ""
                
            cap = determine_capability(file, content)
            score = determine_yield_score(filepath)
            
            target_dir = determine_target_dir(score, cap)
            
            # Conservar ruta relativa original
            relative = filepath.relative_to(src_dir)
            target_path = target_dir / relative
            
            art_id = f"artifact_{artifact_id_counter:03d}"
            artifact_id_counter += 1
            
            status = "active" if score >= 8 else ("archive" if score >= 4 else "graveyard")
            
            inv_entry = {
                "id": art_id,
                "name": file,
                "status": status,
                "domain": cap,
                "yield_score": score,
                "original_path": str(filepath.relative_to(BASE_DIR)),
                "new_path": str(target_path.relative_to(BASE_DIR))
            }
            
            inventory["artifacts"].append(inv_entry)
            
            if status == "active":
                inventory["capabilities"][cap].append(file)
            
            # Move file
            if not DRY_RUN and score >= 8:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if filepath.exists() and not target_path.exists():
                    shutil.move(str(filepath), str(target_path))
            elif DRY_RUN:
                print(f"[DRY] {filepath.relative_to(BASE_DIR)} -> {target_path.relative_to(BASE_DIR)}")

with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
    yaml.dump(inventory, f, sort_keys=False, default_flow_style=False)

print(f"\nInventory generated with {len(inventory['artifacts'])} items in {INVENTORY_FILE}")

# System dirs
print("\nSystem Dir Moves:")
SYSTEM_DIRS = ["cortex", "cortex_kernel", "cortex_rs", "cortex_core_rs", "memory", "ledger", "agent-runtime"]
for sys_dir in SYSTEM_DIRS:
    src = BASE_DIR / sys_dir
    if src.exists() and src.is_dir():
        target = ANTI_GRAVITY_DIR / "02_SYSTEMS" / sys_dir
        if not DRY_RUN:
            if not target.exists():
                shutil.move(str(src), str(target))
                print(f"Moved {sys_dir} to 02_SYSTEMS")
        else:
            print(f"[DRY] {src.relative_to(BASE_DIR)} -> {target.relative_to(BASE_DIR)}")

print("\nDONE. DRY_RUN mode was:", DRY_RUN)
