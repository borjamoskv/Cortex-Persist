# [C5-REAL] Exergy-Maximized
"""
cat_id: run-eviction-simulation
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import os
import sys
import subprocess
import json
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Representative core tests to keep execution fast but statistically significant
DEFAULT_TEST_TARGETS = [
    "tests/test_version_consistency.py",
    "tests/babylon60/test_shadow_tracer.py",
    "tests/test_decoupling.py",
    "tests/test_result.py"
]

def run_mode(mode: str, targets: list[str]) -> dict:
    print(f"\n========================================================")
    print(f"🚀 RUNNING EVICTION SIMULATION IN MODE: [ {mode.upper()} ]")
    print(f"========================================================")
    
    env = os.environ.copy()
    env["CORTEX_SHADOW_MODE"] = mode
    
    # We write compatibility JSON output specifically named after the mode
    report_file = PROJECT_ROOT / f"compatibility_delta_graph_{mode}.json"
    if report_file.exists():
        report_file.unlink()
        
    cmd = ["pytest"] + targets + ["-v"]
    
    try:
        # Run pytest
        res = subprocess.run(
            cmd,
            env=env,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        passed = (res.returncode == 0)
        print(f"Status: {'SUCCESS' if passed else 'FAILED'}")
        
        # Read the generated report
        if report_file.exists():
            with open(report_file, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            return {
                "mode": mode,
                "passed": passed,
                "exit_code": res.returncode,
                "metrics": report_data.get("metrics", {}),
                "uncollapsed_cycles": report_data.get("uncollapsed_cycles", []),
                "collapsed_cycles": report_data.get("collapsed_cycles", []),
                "would_break_count": len(report_data.get("would_breaks", [])),
                "redirects_count": len(report_data.get("redirects", [])),
                "raw_report_path": str(report_file)
            }
        else:
            return {
                "mode": mode,
                "passed": passed,
                "exit_code": res.returncode,
                "metrics": {},
                "uncollapsed_cycles": [],
                "collapsed_cycles": [],
                "would_break_count": 0,
                "redirects_count": 0,
                "raw_report_path": None,
                "error": "No compatibility graph was exported."
            }
            
    except Exception as e:
        print(f"Error running simulation for mode {mode}: {e}")
        return {
            "mode": mode,
            "passed": False,
            "exit_code": -1,
            "metrics": {},
            "uncollapsed_cycles": [],
            "collapsed_cycles": [],
            "would_break_count": 0,
            "redirects_count": 0,
            "error": str(e)
        }

def generate_markdown_report(results: dict) -> str:
    md = []
    md.append("# 📊 BABYLON-60 Cortex Eviction Simulation Report")
    md.append("\nThis report summarizes the compatibility metrics and import graph stability of the active strangler fig migration.")
    
    md.append("\n## 1. Simulation Matrix Summary\n")
    md.append("| Simulation Mode | Execution Status | Traced Modules | Would-Break Nodes | Redirected Nodes | Collapsed Cycles |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    
    for mode in ("present", "shadow-disabled", "redirected"):
        res = results.get(mode, {})
        status = "🟢 PASS" if res.get("passed") else f"🔴 FAIL (Code {res.get('exit_code')})"
        metrics = res.get("metrics", {})
        total_traced = metrics.get("total_traced_modules", "N/A")
        would_break = res.get("would_break_count", 0)
        redirects = res.get("redirects_count", 0)
        collapsed_cycles = len(res.get("collapsed_cycles", []))
        
        md.append(f"| **{mode}** | {status} | {total_traced} | {would_break} | {redirects} | {collapsed_cycles} |")
        
    md.append("\n## 2. Stability Analysis")
    
    # Analyze Present Mode Cycles
    present_res = results.get("present", {})
    uncollapsed = present_res.get("uncollapsed_cycles", [])
    collapsed = present_res.get("collapsed_cycles", [])
    
    md.append(f"\n- **Uncollapsed Import Cycles**: {len(uncollapsed)}")
    if uncollapsed:
        md.append("  > [!WARNING]")
        md.append("  > Legacy import cycles detected in the current codebase:")
        for cycle in uncollapsed:
            md.append(f"  > - `{' -> '.join(cycle)}`")
            
    md.append(f"- **Collapsed Import Cycles (cortex → babylon60)**: {len(collapsed)}")
    if collapsed:
        md.append("  > [!CAUTION]")
        md.append("  > **Graph Stability Hazard:** Collapse of the namespace to `babylon60` will induce the following cycles:")
        for cycle in collapsed:
            md.append(f"  > - `{' -> '.join(cycle)}`")
    else:
        md.append("  > [!NOTE]")
        md.append("  > **Graph Stability Confirmed:** No cycles will be induced if all cortex namespaces collapse to babylon60.")

    md.append("\n## 3. Recommended Actions")
    if len(collapsed) > 0:
        md.append("1. **Resolve Induced Cycles**: Re-architect the imports that cause cycle induction before executing Wave 3 (removal).")
    else:
        md.append("1. **Grafo de Imports Seguro**: El grafo es acíclico bajo colapso. Se puede avanzar a Wave 2 físicamente (mover archivos) con total seguridad.")
    md.append("2. **Eliminación Progresiva**: Convertir los 'would-break' nodes en reemplazos físicos bajo `babylon60/` progresivamente.")
    
    report_path = PROJECT_ROOT / "compatibility_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    
    print(f"\n[C5-REAL] Detailed markdown report generated at: {report_path}")
    return "\n".join(md)

def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TEST_TARGETS
    results = {}
    
    # Run present mode
    results["present"] = run_mode("present", targets)
    
    # Run shadow-disabled mode
    results["shadow-disabled"] = run_mode("shadow-disabled", targets)
    
    # Run redirected mode
    results["redirected"] = run_mode("redirected", targets)
    
    # Generate consolidated markdown
    generate_markdown_report(results)

if __name__ == "__main__":
    main()
