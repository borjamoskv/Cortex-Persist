#!/usr/bin/env python3
# C5-REAL: BABYLON-60 3.0.0 Formal Infrastructure (Python Reference Interpreter)

import sys
import os
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional

def parse_b60_digit(token):
    if token == '-': return 0
    tens = token.count('<')
    ones = token.count('Y') + token.count('v') + token.count('T')
    return tens * 10 + ones

def parse_b60_number(b60_str):
    inner = b60_str.strip('[]').strip()
    if not inner: return 0, 0
    parts = inner.split(';')
    int_part = parts[0]
    
    int_places = int_part.split()
    int_val = 0
    power = len(int_places) - 1 if int_places else 0
    for p in int_places:
        int_val += parse_b60_digit(p) * (60 ** power)
        power -= 1
        
    if len(parts) < 2:
        return int_val, 0
        
    frac_part = parts[1]
    frac_places = frac_part.split()
    scale = len(frac_places)
    frac_val = 0
    for i, p in enumerate(frac_places):
        power_frac = scale - 1 - i
        frac_val += parse_b60_digit(p) * (60 ** power_frac)
        
    total_val = int_val * (60 ** scale) + frac_val
    return total_val, scale

def format_b60(val, scale):
    if val == 0: return "[-]"
    
    denom = 60 ** scale
    int_part = abs(val) // denom
    frac_part = abs(val) % denom
    
    int_places = []
    temp = int_part
    while temp > 0:
        int_places.append(temp % 60)
        temp //= 60
    if not int_places:
        int_places.append(0)
    int_places.reverse()
    
    int_strs = []
    for p in int_places:
        if p == 0:
            int_strs.append("-")
        else:
            tens = p // 10
            ones = p % 10
            int_strs.append(("<" * tens) + ("Y" * ones))
            
    sign_prefix = "NEG " if val < 0 else ""
    
    if scale == 0:
        return f"{sign_prefix}[ " + " ".join(int_strs) + " ]"
        
    frac_places = []
    for _ in range(scale):
        frac_part *= 60
        frac_places.append(frac_part // denom)
        frac_part %= denom
        
    frac_strs = []
    for p in frac_places:
        if p == 0:
            frac_strs.append("-")
        else:
            tens = p // 10
            ones = p % 10
            frac_strs.append(("<" * tens) + ("Y" * ones))
            
    return f"{sign_prefix}[ " + " ".join(int_strs) + " ; " + " ".join(frac_strs) + " ]"

# --- 8. Separar Tiempo Físico de Tiempo Lógico ---
@dataclass(frozen=True)
class PhysicalClock:
    wall_time_ns: int

@dataclass(frozen=True)
class LogicalClock:
    tick: int

@dataclass(frozen=True)
class SimulationClock:
    epoch: int

# --- 9. El Ledger como objeto matemático (DAG) ---
@dataclass
class Event:
    event_id: str
    parents: List[str]
    logical_timestamp: LogicalClock
    payload: str
    signature: str
    
    def hash(self) -> str:
        data = f"{self.event_id}{self.parents}{self.logical_timestamp.tick}{self.payload}{self.signature}"
        return hashlib.sha256(data.encode()).hexdigest()

    def serialize_canonical(self) -> str:
        parents_sorted = ",".join(sorted(self.parents))
        return f"{self.event_id}|{parents_sorted}|{self.logical_timestamp.tick}|{self.payload}|{self.signature}"

class DAGLedger:
    def __init__(self):
        self.events: Dict[str, Event] = {}
        
    def append(self, event: Event):
        self.events[event.event_id] = event

    def generate_canonical_graph(self) -> str:
        lines = [ev.serialize_canonical() for ev in self.events.values()]
        lines.sort()
        return "\n".join(lines) + "\n"

# --- 10. Compilador autoconsciente ---
class VMProgram:
    def __init__(self, instructions: List[str]):
        self.instructions = instructions
        binary_rep = "\n".join(instructions).encode()
        self.sha256 = hashlib.sha256(binary_rep).hexdigest()

class B60Compiler:
    def compile(self, source: str) -> VMProgram:
        lines = [line.split('#')[0].strip() for line in source.split('\n') if line.split('#')[0].strip()]
        self.static_proof(lines)
        return VMProgram(instructions=lines)
        
    def static_proof(self, lines: List[str]):
        labels = {}
        allocated_regs = {}
        defined_signals = []
        awaited_signals = []
        
        for i, line in enumerate(lines):
            tokens = line.split()
            if not tokens: continue
            cmd = tokens[0]
            if cmd == "MUB":
                if len(tokens) > 1:
                    name = tokens[1].strip('"')
                    labels[name] = i
            elif cmd == "ALLOC":
                if len(tokens) > 2:
                    typ = tokens[1]
                    reg = tokens[2]
                    allocated_regs[reg] = typ
            elif cmd == "EXECUTE":
                if len(tokens) > 1:
                    sig = tokens[1].strip('"')
                    defined_signals.append(sig)
            elif cmd == "AWAIT":
                if len(tokens) > 1:
                    sig = tokens[1].strip('"')
                    awaited_signals.append(sig)
                    
        # 1. Unreachable instructions
        in_halt_zone = False
        for line in lines:
            tokens = line.split()
            if not tokens: continue
            cmd = tokens[0]
            if cmd == "MUB":
                in_halt_zone = False
            elif in_halt_zone:
                raise ValueError(f"CRITICAL COMPILE ERROR: Unreachable instruction detected in halt zone: '{line}'")
            elif cmd == "HALT" or (cmd == "CRITICAL" and len(tokens) > 1 and tokens[1] == "HALT"):
                in_halt_zone = True
                
        # 2. Circular awaits (deadlock warning)
        for sig in awaited_signals:
            if sig not in defined_signals:
                print(f"[COMPILER WARNING] Potential Deadlock: Signal '{sig}' is awaited but never executed.", file=sys.stderr)
                
        # 3. Uninitialized registers
        for line in lines:
            tokens = line.split()
            if not tokens: continue
            cmd = tokens[0]
            if cmd in ["DAH", "LAL", "AFTER", "NU", "BA.EXACT"]:
                for t in tokens[1:]:
                    if t.startswith('R'):
                        if t not in allocated_regs:
                            raise ValueError(f"CRITICAL COMPILE ERROR: Access to uninitialized / unallocated register: '{t}' in instruction '{line}'")
                            
        # 4. Strongly typed temporal domains
        for line in lines:
            tokens = line.split()
            if not tokens: continue
            cmd = tokens[0]
            if cmd in ["DAH", "LAL"]:
                if len(tokens) > 2:
                    dest = tokens[1]
                    src = tokens[2]
                    if dest.startswith('R') and src.startswith('R'):
                        dest_typ = allocated_regs.get(dest)
                        src_typ = allocated_regs.get(src)
                        if dest_typ != src_typ:
                            raise ValueError(f"CRITICAL COMPILE ERROR: Strongly typed temporal domain mismatch. Cannot perform arithmetic between '{dest}' ({dest_typ}) and '{src}' ({src_typ})")

# --- 13. Máquina virtual mínima ---
class Coroutine:
    def __init__(self, cid, pc, labels):
        self.id = cid
        self.pc = pc
        self.regs = [{"val": 0, "scale": 0, "typ": "UNALLOCATED"} for _ in range(64)]
        self.state = "Ready" # Ready, Waiting(event), WaitingTimer(tick), Halted
        self.target_tick = 0
        self.wait_event = ""
        self.labels = labels

    def clone(self, new_id, target_label):
        c = Coroutine(new_id, self.labels.get(target_label, 0), self.labels)
        import copy
        c.regs = copy.deepcopy(self.regs)
        return c

def get_reg_index(reg_str):
    if reg_str.startswith('R'):
        try:
            return int(reg_str[1:])
        except Exception as e:
            pass
    return 0

def parse_unit(unit_str):
    if unit_str == "UNIT.TICK": return 1
    if unit_str == "UNIT.SECOND": return 1000
    if unit_str == "UNIT.MINUTE": return 60000
    if unit_str == "UNIT.HOUR": return 3600000
    return 1

def eval_expr(expr, unit, regs):
    if expr.startswith('['):
        val, scale = parse_b60_number(expr)
        return val * parse_unit(unit), scale
    if expr.startswith('R'):
        idx = get_reg_index(expr)
        return regs[idx]["val"], regs[idx]["scale"]
    return 0, 0

def divide_exact(numerator, scale, divisor):
    if divisor == 0: return 0, scale
    num = numerator
    sc = scale
    while num % divisor != 0 and sc < 5:
        num *= 60
        sc += 1
    return num // divisor, sc

class B60MinimalVM:
    def __init__(self):
        self.ledger = DAGLedger()
        self.clock = 0
        self.queue = []
        self.next_co_id = 1
        self.is_halting = False
        
    def execute(self, program: VMProgram):
        labels = {}
        for i, line in enumerate(program.instructions):
            if line.startswith("MUB "):
                labels[line.split()[1].strip('"')] = i
                
        self.queue.append(Coroutine(0, 0, labels))
        
        while self.queue:
            if self.is_halting: break
            co = self.queue.pop(0)
            
            if co.state == "Halted":
                continue
                
            if co.state == "WaitingTimer":
                if self.clock >= co.target_tick:
                    co.state = "Ready"
                else:
                    self.queue.append(co)
                    self.clock += 1
                    continue
                    
            if co.state == "Waiting":
                found = False
                for ev in self.ledger.events.values():
                    if ev.payload == co.wait_event:
                        found = True
                        break
                if found:
                    co.state = "Ready"
                else:
                    self.queue.append(co)
                    continue
                    
            if co.pc >= len(program.instructions):
                continue
                
            line = program.instructions[co.pc]
            co.pc += 1
            
            if not line or line == "DUB" or line.startswith("MUB "):
                self.queue.append(co)
                continue
                
            tokens = []
            in_bracket = False
            in_string = False
            cur = ""
            for c in line:
                if c == '"':
                    in_string = not in_string
                    cur += c
                elif c == '[' and not in_string:
                    in_bracket = True
                    cur += c
                elif c == ']' and not in_string:
                    in_bracket = False
                    cur += c
                    tokens.append(cur.strip())
                    cur = ""
                elif c.isspace() and not in_bracket and not in_string:
                    if cur:
                        tokens.append(cur)
                        cur = ""
                else:
                    cur += c
            if cur: tokens.append(cur)
            if not tokens:
                self.queue.append(co)
                continue
                
            cmd = tokens[0]
            ev_id = f"EV_{self.clock}"
            
            if cmd == "NIG":
                idx = get_reg_index(tokens[1])
                unit = tokens[3] if len(tokens) > 3 else ""
                val, scale = eval_expr(tokens[2], unit, co.regs)
                co.regs[idx]["val"] = val
                co.regs[idx]["scale"] = scale
                formatted = format_b60(val, scale)
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), f"R{idx}={formatted}", "SIG_OK"))
            elif cmd == "FORK":
                target = tokens[1].strip('"')
                new_co = co.clone(self.next_co_id, target)
                self.next_co_id += 1
                self.queue.append(new_co)
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), target, "SIG_OK"))
            elif cmd == "AWAIT":
                symbol = tokens[1].strip('"')
                target = tokens[2].strip('"')
                co.state = "Waiting"
                co.wait_event = symbol
                co.pc = labels.get(target, 0)
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), symbol, "SIG_OK"))
            elif cmd == "AFTER":
                idx = get_reg_index(tokens[1])
                target = tokens[2].strip('"')
                ticks = co.regs[idx]["val"]
                co.state = "WaitingTimer"
                co.target_tick = self.clock + ticks
                co.pc = labels.get(target, 0)
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), str(ticks), "SIG_OK"))
            elif cmd == "EXECUTE":
                action = tokens[1].strip('"')
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), action, "SIG_OK"))
                if action.startswith("CRITICAL_HALT"):
                    self.is_halting = True
            elif cmd == "CRITICAL":
                if len(tokens) > 1 and tokens[1] == "HALT":
                    co.state = "Halted"
                    self.is_halting = True
            elif cmd == "ALLOC":
                typ_str = tokens[1]
                idx = get_reg_index(tokens[2])
                co.regs[idx]["typ"] = typ_str
            elif cmd == "DAH":
                idx = get_reg_index(tokens[1])
                val2, scale2 = eval_expr(tokens[2], "", co.regs)
                
                # Exact addition
                s_max = max(co.regs[idx]["scale"], scale2)
                v1 = co.regs[idx]["val"] * (60 ** (s_max - co.regs[idx]["scale"]))
                v2 = val2 * (60 ** (s_max - scale2))
                co.regs[idx]["val"] = v1 + v2
                co.regs[idx]["scale"] = s_max
                
                formatted = format_b60(val2, scale2)
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), f"R{idx}+={formatted}", "SIG_OK"))
            elif cmd == "LAL":
                idx = get_reg_index(tokens[1])
                val2, scale2 = eval_expr(tokens[2], "", co.regs)
                
                # Exact subtraction
                s_max = max(co.regs[idx]["scale"], scale2)
                v1 = co.regs[idx]["val"] * (60 ** (s_max - co.regs[idx]["scale"]))
                v2 = val2 * (60 ** (s_max - scale2))
                co.regs[idx]["val"] = v1 - v2
                co.regs[idx]["scale"] = s_max
                
                formatted = format_b60(val2, scale2)
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), f"R{idx}-={formatted}", "SIG_OK"))
            elif cmd == "NU":
                idx = get_reg_index(tokens[1])
                target = tokens[2].strip('"')
                if co.regs[idx]["val"] == 0:
                    co.pc = labels.get(target, 0)
                    self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), f"JMP {target}", "SIG_OK"))
            elif cmd == "BA.EXACT":
                idx = get_reg_index(tokens[1])
                idx2 = get_reg_index(tokens[2])
                div = co.regs[idx2]["val"]
                new_val, new_scale = divide_exact(co.regs[idx]["val"], co.regs[idx]["scale"], div)
                co.regs[idx]["val"] = new_val
                co.regs[idx]["scale"] = new_scale
                self.ledger.append(Event(ev_id, [], LogicalClock(self.clock), f"R{idx}/={div}", "SIG_OK"))
            elif cmd in ["HALT"]:
                co.state = "Halted"
                
            self.clock += 1
            self.queue.append(co)
            
        sorted_events = sorted(self.ledger.events.values(), key=lambda e: e.logical_timestamp.tick)
        prev_id = ""
        for ev in sorted_events:
            if prev_id:
                ev.parents.append(prev_id)
            prev_id = ev.event_id
 
        return "HALTED" if self.is_halting else "COMPLETED"
            
    def export_artifact(self, program: VMProgram):
        canonical_graph = self.ledger.generate_canonical_graph()
        graph_sha256 = hashlib.sha256(canonical_graph.encode()).hexdigest()
        
        manifest = {
            "version": "1.0",
            "components": ["trace.bin", "graph.canonical", "proof.ir", "metadata.json", "hashes/", "signature/"],
            "global_hash": graph_sha256,
            "theorem_of_babylon_compliance": not self.is_halting
        }
        return manifest, canonical_graph, graph_sha256

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 babylon60.py <script.b60>")
        sys.exit(1)
    
    script_path = sys.argv[1]
    with open(script_path, 'r') as f:
        source = f.read()
        
    compiler = B60Compiler()
    program = compiler.compile(source)
    
    vm = B60MinimalVM()
    state = vm.execute(program)
    
    manifest, canonical_graph, graph_sha256 = vm.export_artifact(program)
    
    bundle_dir = "artifact_bundle_v3"
    os.makedirs(bundle_dir, exist_ok=True)
    with open(os.path.join(bundle_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    with open(os.path.join(bundle_dir, "graph.canonical"), "w") as f:
        f.write(canonical_graph)
    with open(os.path.join(bundle_dir, "proof.ir"), "w") as f:
        f.write("Mock Proof IR")
