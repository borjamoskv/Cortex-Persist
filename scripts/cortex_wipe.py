#!/usr/bin/env python3
"""
cortex_wipe.py
SYS_ID: borjamoskv · Aesthetic: Industrial Noir 2026

CLI Utility for Safe Device Sanitization complying with NIST SP 800-88 guidelines.
Distinguishes Rotational HDDs from NAND SSDs to execute correct hardware-level erase.
"""

import os
import sys
import argparse
import subprocess
import json

def get_device_info(device_path):
    """
    Queries sysfs to check if the target disk is rotational or solid-state.
    """
    device_name = os.path.basename(device_path)
    # Target path in sysfs for rotational status
    sys_path = f"/sys/class/block/{device_name}/queue/rotational"
    if not os.path.exists(sys_path):
        # Check if parent device path works
        parent_name = "".join([c for c in device_name if not c.isdigit()])
        sys_path = f"/sys/class/block/{parent_name}/queue/rotational"
        if not os.path.exists(sys_path):
            raise FileNotFoundError(f"Cannot determine physical properties for: {device_path}")

    with open(sys_path, "r") as f:
        is_rotational = f.read().strip() == "1"
    
    return {
        "device": device_path,
        "rotational": is_rotational,
        "type": "HDD (Rotational)" if is_rotational else "SSD (Solid-State/NAND)"
    }

def execute_command(cmd, dry_run=True):
    print(f"Executing: {' '.join(cmd)}")
    if dry_run:
        print("[DRY-RUN] Command simulated successfully.")
        return 0
    
    try:
        res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(res.stdout.decode())
        return res.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error during execution: {e.stderr.decode()}", file=sys.stderr)
        return e.returncode

def main():
    parser = argparse.ArgumentParser(description="cortex_wipe.py: Hardware-Aware Sanitization Tool")
    parser.add_argument("device", help="Target block device (e.g., /dev/sdb or /dev/nvme0n1)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate commands without writing (default: True)")
    parser.add_argument("--force-execute", action="store_false", dest="dry_run", help="Disable dry-run and commit changes to disk")
    
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("CRITICAL: Root permissions required.", file=sys.stderr)
        sys.exit(1)

    try:
        info = get_device_info(args.device)
        print(json.dumps(info, indent=2))
    except Exception as e:
        print(f"Error reading device parameters: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n--- SANITIZATION STRATEGY ---")
    if not info["rotational"]:
        print("Device is SSD. Traditional multi-pass logical wipe is forbidden (Write Amplification / Ineffective FTL bypass).")
        if "nvme" in args.device:
            print("Selected: NVMe Cryptographic/Format Erase")
            # Format NVMe with user-data erase (ses=1: User Data Erase, ses=2: Cryptographic Erase)
            cmd = ["nvme", "format", args.device, "--namespace-id=1", "--ses=1"]
        else:
            print("Selected: ATA Secure Erase via hdparm")
            print("Ensure device is not FROZEN. (Check: hdparm -I /dev/device)")
            cmd = ["hdparm", "--user-master", "u", "--security-erase", "NULL", args.device]
    else:
        print("Device is HDD. Executing zeroing with random pass fallback.")
        cmd = ["dd", "if=/dev/urandom", f"of={args.device}", "bs=4M", "status=progress", "conv=fdatasync"]

    print("")
    execute_command(cmd, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
