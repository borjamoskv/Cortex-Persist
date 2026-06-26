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
        "def Val: Type := Int",
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
            # Assign R1 601 EV_0
            lean_code.append(f"axiom assign_{parts[3]} : Val := {parts[2]}")
        elif tag == "Add":
            lean_code.append(f"axiom add_{parts[3]} : Val := {parts[2]}")
        elif tag == "Sub":
            lean_code.append(f"axiom sub_{parts[3]} : Val := {parts[2]}")
        elif tag == "Spawn":
            lean_code.append(f"axiom spawn_{parts[2]} : String := \"{parts[1]}\"")
        elif tag == "Block":
            lean_code.append(f"axiom await_{parts[2]} : String := \"{parts[1]}\"")
        elif tag == "Wait":
            lean_code.append(f"axiom after_{parts[2]} : Nat := {parts[1]}")
        elif tag == "Emit":
            lean_code.append(f"axiom emit_{parts[2]} : String := \"{parts[1]}\"")

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
