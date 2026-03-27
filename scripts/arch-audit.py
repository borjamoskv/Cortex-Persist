import hashlib
import logging
import os
import subprocess
import sys

# Ω₄₀: Structural Integrity & Taint Tracking
# Ω₄₆: Real Semantic Merkle
# Ω₅₂: Predictive Entropy (Git-Based)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("arch-audit")

def compute_path_hash(path):
    """Ω₄₆: Real Semantic Merkle - Compute SHA-256 for a file or directory."""
    hasher = hashlib.sha256()
    if os.path.isfile(path):
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
    else:
        for root, _, files in os.walk(path):
            for name in sorted(files):
                if name.startswith('.') or 'scripts' in root:
                    continue
                file_path = os.path.join(root, name)
                try:
                    with open(file_path, "rb") as f:
                        while chunk := f.read(8192):
                            hasher.update(chunk)
                except OSError:
                    continue
    return hasher.hexdigest()

def get_predictive_drift(target_path):
    """Ω₅₂: Analyze git history for 'hot' files and commit frequency."""
    try:
        # Get top 5 most modified files in the last 30 days
        result = subprocess.run(
            ["git", "log", "--since='30 days ago'", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, check=True
        )
        files = [f for f in result.stdout.splitlines() if f.strip()]
        from collections import Counter
        counts = Counter(files)
        return dict(counts.most_common(5))
    except Exception:
        return {}

def run_arch_audit(target_path):
    logger.info(f"--- 📐 ARCH-AUDIT Ω₄₀/Ω₄₆/Ω₅₂: {target_path} ---")
    
    # 1. Ω₄₆: Real Semantic Merkle
    current_hash = compute_path_hash(target_path)
    logger.info(f"Ω₄₆-HASH: {current_hash}")
    
    # 2. Ω₅₂: Predictive Entropy (Git)
    drift = get_predictive_drift(target_path)
    if drift:
        logger.info(f"Ω₅₂-PREDICTIVE-HOT-FILES: {drift}")
    
    # 3. Ω₄₀: Taint Tracking
    files_to_check = [target_path] if os.path.isfile(target_path) else []
    if not files_to_check:
        for root, _, files in os.walk(target_path):
            for name in files:
                if name.endswith(".py"):
                    files_to_check.append(os.path.join(root, name))
    
    tainted_files = []
    for f_path in files_to_check:
        if not f_path.endswith(".py"): continue
        try:
            with open(f_path) as f:
                content = f.read()
                if "DECORATIVE" in content or "metaphor" in content.lower():
                    tainted_files.append(os.path.basename(f_path))
        except Exception:
            continue
    
    score = 1.0
    if tainted_files:
        logger.warning(f"Ω₄₀-TAINT-DETECTED: {len(tainted_files)} files contaminated.")
        score -= 0.5
        
    # Apply predictive penalty if hot files are many
    if len(drift) > 3:
        logger.warning("Ω₅₂-PREDICTION: High activity detected. Increasing probability of collision.")
        score -= 0.1

    return max(0.0, score)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    final_score = run_arch_audit(target)
    print(f"RESULT: {final_score}")
