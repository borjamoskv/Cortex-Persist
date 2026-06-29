# [C5-REAL] Exergy-Maximized
"""
cat_id: release-preflight
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import sys
import tarfile
import zipfile
from pathlib import Path

import tomllib

BLACKLIST = {'.env', 'scratch', '__pycache__', '.pytest_cache', '.git'}

def die(msg: str):
    print(f"[C5-REAL PREFLIGHT FATAL] {msg}", file=sys.stderr)
    sys.exit(1)

def get_project_version() -> str:
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception as e:
        die(f"Failed to read pyproject.toml: {e}")

def check_entropy(names: list[str], context: str):
    for name in names:
        parts = Path(name).parts
        for part in parts:
            if part in BLACKLIST:
                die(f"Anergy detected in {context}: Forbidden path component '{part}' in '{name}'")

def run_preflight():
    print("[C5-REAL PREFLIGHT] Initializing artifact audit...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists() or not dist_dir.is_dir():
        die("dist/ directory not found. Run 'python3 -m build' first.")
        
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    
    if len(wheels) != 1:
        die(f"Expected exactly 1 wheel, found {len(wheels)}")
    if len(sdists) != 1:
        die(f"Expected exactly 1 sdist, found {len(sdists)}")
        
    wheel_path = wheels[0]
    sdist_path = sdists[0]
    
    project_version = get_project_version()
    print(f"Project version defined as: {project_version}")
    
    # Check wheel version match
    wheel_stem = wheel_path.name.split("-")
    if len(wheel_stem) < 2 or wheel_stem[1] != project_version:
        die(f"Wheel version mismatch. Expected {project_version}, got {wheel_path.name}")
        
    # Check sdist version match
    if not sdist_path.name.endswith(f"-{project_version}.tar.gz"):
        die(f"Sdist version mismatch. Expected to end with -{project_version}.tar.gz, got {sdist_path.name}")

    # Inspect Wheel contents
    print(f"[C5-REAL PREFLIGHT] Scanning Wheel: {wheel_path.name}")
    with zipfile.ZipFile(wheel_path, 'r') as zf:
        check_entropy(zf.namelist(), "Wheel")

    # Inspect Sdist contents
    print(f"[C5-REAL PREFLIGHT] Scanning Sdist: {sdist_path.name}")
    with tarfile.open(sdist_path, 'r:gz') as tf:
        check_entropy(tf.getnames(), "Sdist")

    print("[C5-REAL PREFLIGHT] Audit PASSED. Artifacts are mathematically sound for PyPI.")

if __name__ == "__main__":
    run_preflight()
