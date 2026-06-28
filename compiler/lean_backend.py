#!/usr/bin/env python3
# C5-REAL: Lean 4 Translation Backend for BABYLON-60 Proof IR

import sys
import os

def parse_ir(file_path):
    with open(file_path, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines

def translate_to_lean(ir_lines):
    lean_code = [
        "-- Auto-generated Lean 4 Backend for BABYLON-60",
        "import Mathlib",
        "",
        "namespace Babylon60",
        "",
        "-- Core state declarations",
        "def Reg: Type := Nat",
        "def Val: Type := String", # Represent B60 values as String for exact sexagesimal support
        "def EventId: Type := String",
        "",
        "-- Axiomatic Trace Declarations",
    ]

    for line in ir_lines:
        line = line.strip("()")
        parts = line.split()
        if not parts:
            continue
        
        tag = parts[0]
        if tag == "Event":
            lean_code.append(f"axiom ev_tick_{parts[1]} : Nat := {parts[2]}")
        elif tag == "HappensBefore":
            lean_code.append(f"axiom causal_{parts[1]}_{parts[2]} : ev_tick_{parts[1]} ≤ ev_tick_{parts[2]}")
        elif tag == "Assign":
            event_id = parts[-1]
            reg = parts[1]
            val = " ".join(parts[2:-1])
            lean_code.append(f"axiom assign_{event_id} : Val := \"{val}\"")
        elif tag == "Add":
            event_id = parts[-1]
            reg = parts[1]
            val = " ".join(parts[2:-1])
            lean_code.append(f"axiom add_{event_id} : Val := \"{val}\"")
        elif tag == "Sub":
            event_id = parts[-1]
            reg = parts[1]
            val = " ".join(parts[2:-1])
            lean_code.append(f"axiom sub_{event_id} : Val := \"{val}\"")
        elif tag == "Spawn":
            event_id = parts[-1]
            target = " ".join(parts[1:-1])
            lean_code.append(f"axiom spawn_{event_id} : String := \"{target}\"")
        elif tag == "Block":
            event_id = parts[-1]
            symbol = " ".join(parts[1:-1])
            lean_code.append(f"axiom await_{event_id} : String := \"{symbol}\"")
        elif tag == "Wait":
            event_id = parts[-1]
            ticks = parts[1]
            lean_code.append(f"axiom after_{event_id} : Nat := {ticks}")
        elif tag == "Emit":
            event_id = parts[-1]
            action = " ".join(parts[1:-1])
            lean_code.append(f"axiom emit_{event_id} : String := \"{action}\"")

    lean_code.append("")
    lean_code.append("end Babylon60")
    lean_code.append("")
    
    return "\n".join(lean_code)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 lean_backend.py <path_to_proof.ir>")
        sys.exit(1)
        
    ir_file = sys.argv[1]
    if not os.path.exists(ir_file):
        print(f"Error: {ir_file} not found.")
        sys.exit(1)
        
    ir_lines = parse_ir(ir_file)
    lean_code = translate_to_lean(ir_lines)
    
    out_file = "BabylonTrace.lean"
    with open(out_file, "w") as f:
        f.write(lean_code)
        
    print(f"[Lean Backend] Generated {out_file} successfully.")

if __name__ == "__main__":
    main()
