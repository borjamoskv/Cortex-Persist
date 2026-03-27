import logging
import os
import sys

# Ω₄₁: Vision Proxy Architecture
# Ω₅₃: Aesthetic Drift Detection (Visual Rot)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("aesthetic-cli")

def detect_visual_rot(target_path):
    """Ω₅₃: Analyze asset growth vs. usage."""
    rot_found = False
    css_files = []
    if os.path.isdir(target_path):
        for root, _, files in os.walk(target_path):
            for name in files:
                if name.endswith(".css"):
                    css_files.append(os.path.join(root, name))
    
    # Simple rot check: large CSS files with zero or low usage of variables
    for css in css_files:
        try:
            size_kb = os.path.getsize(css) / 1024
            if size_kb > 50: # Arbitrary threshold for "potential rot" in components
                with open(css) as f:
                    content = f.read()
                    if "--" not in content:
                        logger.warning(f"Ω₅₃-ROT: {os.path.basename(css)} is large but has few custom properties.")
                        rot_found = True
        except Exception:
            continue
    return rot_found

def run_aesthetic_audit(target_path):
    logger.info(f"--- ✨ AESTHETIC-AUDIT Ω₄₁/Ω₅₃: {target_path} ---")
    
    # 1. Ω₄₁ Vision Proxy Simulation
    files_to_check = []
    if os.path.isfile(target_path):
        files_to_check.append(target_path)
    else:
        for root, _, files in os.walk(target_path):
            for name in files:
                if name.endswith((".html", ".css", ".astro")):
                    files_to_check.append(os.path.join(root, name))
    
    score = 1.0
    violations = 0
    for f_path in files_to_check:
        try:
            with open(f_path) as f:
                content = f.read()
                # Check for Industrial Noir violations
                if any(x in content for x in ["#ffffff", "white", "arial"]):
                    violations += 1
        except Exception:
            continue
            
    if violations > 0:
        logger.warning(f"Ω₄₁-VISION-FAIL: {violations} aesthetic violations detected.")
        score -= min(0.5, violations * 0.1)

    # 2. Ω₅₃ Aesthetic Drift
    if detect_visual_rot(target_path):
        score -= 0.1

    return max(0.0, score)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    final_score = run_aesthetic_audit(target)
    print(f"RESULT: {final_score}")
