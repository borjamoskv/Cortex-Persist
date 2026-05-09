import os
import subprocess
import json
import shutil

def run_test():
    print("============================================================")
    print("  CORTEX Anchoring E2E Test")
    print("============================================================")

    # Clean up old database and artifacts
    for f in ["scratch/test_compliance.db", "scratch/audit_report.json", "scratch/evidence_manifest.json"]:
        if os.path.exists(f):
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.remove(f)

    project_name = "test-anchoring"

    # 0. Seed Data
    print(f"\n[0] Seeding dummy fact for project '{project_name}'...")
    cmd = [
        "python3", "-m", "cortex.cli.main", "memory", "store",
        project_name, "anchoring-test-payload",
        "--type", "knowledge"
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["CORTEX_DB"] = "scratch/test_compliance.db"
    env["CORTEX_MASTER_KEY"] = "1b4ATlqSpPMD4dwLuu6QPezppXcvR2GqQRheBxVaItY="
    env["CORTEX_TESTING"] = "1"
    subprocess.run(cmd, env=env, check=True)
    print("  ✅ Data seeded")

    # 1. Export Compliance Report
    print(f"\n[1] Exporting compliance report for project '{project_name}'...")
    report_path = "scratch/evidence_manifest.json"
    cmd = [
        "python3", "-m", "cortex.cli.main", "audit", "export-compliance",
        "--project", project_name,
        "--output", report_path
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["CORTEX_DB"] = "scratch/test_compliance.db"
    env["CORTEX_MASTER_KEY"] = "1b4ATlqSpPMD4dwLuu6QPezppXcvR2GqQRheBxVaItY="
    env["CORTEX_TESTING"] = "1"
    subprocess.run(cmd, env=env, check=True)
    print(f"  ✅ Exported to {report_path}")

    # 2. Anchor to Manifest
    print("\n[2] Anchoring report to manifest (OpenTimestamps)...")
    # Note: anchor command modifies in-place
    cmd = [
        "python3", "-m", "cortex.cli.main", "audit", "anchor",
        report_path
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["CORTEX_DB"] = "scratch/test_compliance.db"
    env["CORTEX_MASTER_KEY"] = "1b4ATlqSpPMD4dwLuu6QPezppXcvR2GqQRheBxVaItY="
    env["CORTEX_TESTING"] = "1"
    subprocess.run(cmd, env=env, check=True)
    print(f"  ✅ Anchored successfully")

    # 3. Verify Manifest
    print("\n[3] Verifying manifest...")
    cmd = [
        "python3", "-m", "cortex.cli.main", "audit", "verify-manifest",
        report_path
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["CORTEX_DB"] = "scratch/test_compliance.db"
    env["CORTEX_MASTER_KEY"] = "1b4ATlqSpPMD4dwLuu6QPezppXcvR2GqQRheBxVaItY="
    env["CORTEX_TESTING"] = "1"
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("  ✅ Verification PASSED")
        print("\n[SUCCESS] CORTEX Compliance Pipeline is fully functional (Art. 12)")
    else:
        print("  ❌ Verification FAILED")
        print(result.stdout)
        print(result.stderr)
        exit(1)

if __name__ == "__main__":
    run_test()
