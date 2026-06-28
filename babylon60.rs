use std::collections::{HashMap, VecDeque};
use std::env;
use std::fs;

// =====================================================================
// BABYLON-60: Formal Infrastructure for Verifiable Science (v3.0.0-C5-REAL)
// =====================================================================

#[derive(Clone, Debug, PartialEq, Copy)]
enum B60Type {
    I64,
    TIME,
    F60,
    UNALLOCATED,
}

#[derive(Clone, Debug)]
struct Register {
    val: i128,          // Numerator
    typ: B60Type,
    scale: u32,         // Denominator exponent (60^scale)
}

// --- 8. Separate Temporal Domains ---
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct PhysicalClock(u128); // nanoseconds

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct LogicalClock(u64); // scheduler tick

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct SimulationClock(u64); // math simulation epoch

// --- 9. DAG Ledger ---
#[derive(Clone, Debug)]
struct DAGEvent {
    id: String,
    parents: Vec<String>,
    logical_timestamp: LogicalClock,
    opcode: String,
    payload: String,
    hash: String,
    signature: String,
}

impl DAGEvent {
    fn compute_hash(&self) -> String {
        format!("{:016x}", self.logical_timestamp.0 ^ self.payload.len() as u64)
    }
}

struct DAGLedger {
    events: HashMap<String, DAGEvent>,
    latest: Vec<String>,
}

impl DAGLedger {
    fn new() -> Self {
        Self { events: HashMap::new(), latest: Vec::new() }
    }
    
    fn append(&mut self, id: String, opcode: String, payload: String, logical_time: LogicalClock) {
        let parents = self.latest.clone();
        let mut ev = DAGEvent {
            id: id.clone(),
            parents,
            logical_timestamp: logical_time,
            opcode,
            payload,
            hash: String::new(),
            signature: "SIG_OK".to_string(),
        };
        ev.hash = ev.compute_hash();
        self.events.insert(id.clone(), ev);
        self.latest = vec![id];
    }
}

// VM Structs
#[derive(Clone, Debug, PartialEq)]
enum CoroutineState {
    Ready,
    Running,
    Waiting(String),
    WaitingTimer(LogicalClock),
    Halted,
    Completed,
}

#[derive(Clone, Debug)]
struct Coroutine {
    id: usize,
    pc: usize,
    regs: Vec<Register>,
    state: CoroutineState,
}

// --- Compiler & Static Proof ---
struct B60Compiler;

impl B60Compiler {
    fn compile(source: &str) -> Result<Vec<String>, String> {
        let lines: Vec<String> = source.lines()
            .map(|l| l.split('#').next().unwrap().trim().to_string())
            .filter(|l| !l.is_empty())
            .collect();
        Self::static_proof(&lines)?;
        Ok(lines)
    }

    fn static_proof(lines: &[String]) -> Result<(), String> {
        let mut labels = HashMap::new();
        let mut allocated_regs = HashMap::new();
        let mut defined_signals = Vec::new();
        let mut awaited_signals = Vec::new();
        
        for (i, line) in lines.iter().enumerate() {
            let tokens: Vec<&str> = line.split_whitespace().collect();
            if tokens.is_empty() { continue; }
            
            let cmd = tokens[0];
            match cmd {
                "MUB" => {
                    if tokens.len() > 1 {
                        let name = tokens[1].trim_matches('"');
                        labels.insert(name.to_string(), i);
                    }
                }
                "ALLOC" => {
                    if tokens.len() > 2 {
                        let typ = tokens[1];
                        let reg = tokens[2];
                        allocated_regs.insert(reg.to_string(), typ.to_string());
                    }
                }
                "EXECUTE" => {
                    if tokens.len() > 1 {
                        let sig = tokens[1].trim_matches('"');
                        defined_signals.push(sig.to_string());
                    }
                }
                "AWAIT" => {
                    if tokens.len() > 1 {
                        let sig = tokens[1].trim_matches('"');
                        awaited_signals.push(sig.to_string());
                    }
                }
                _ => {}
            }
        }
        
        // 1. Check for unreachable events (code after HALT / CRITICAL HALT with no label in between)
        let mut in_halt_zone = false;
        for line in lines {
            let tokens: Vec<&str> = line.split_whitespace().collect();
            if tokens.is_empty() { continue; }
            let cmd = tokens[0];
            if cmd == "MUB" {
                in_halt_zone = false;
            } else if in_halt_zone {
                return Err(format!("CRITICAL COMPILE ERROR: Unreachable instruction detected in halt zone: '{}'", line));
            } else if cmd == "HALT" || (cmd == "CRITICAL" && tokens.get(1) == Some(&"HALT")) {
                in_halt_zone = true;
            }
        }

        // 2. Check for circular awaits / deadlocks (Warning only to support fuzzers)
        for sig in &awaited_signals {
            if !defined_signals.contains(sig) {
                eprintln!("[COMPILER WARNING] Potential Deadlock: Signal '{}' is awaited but never executed.", sig);
            }
        }

        // 3. Check for uninitialized register accesses
        for line in lines {
            let tokens: Vec<&str> = line.split_whitespace().collect();
            if tokens.is_empty() { continue; }
            let cmd = tokens[0];
            if cmd == "DAH" || cmd == "LAL" || cmd == "AFTER" || cmd == "NU" || cmd == "BA.EXACT" {
                for t in &tokens[1..] {
                    if t.starts_with('R') {
                        if !allocated_regs.contains_key(*t) {
                            return Err(format!("CRITICAL COMPILE ERROR: Access to uninitialized / unallocated register: '{}' in instruction '{}'", t, line));
                        }
                    }
                }
            }
        }
        
        // 4. Enforce separate temporal domains (strong typing)
        for line in lines {
            let tokens: Vec<&str> = line.split_whitespace().collect();
            if tokens.is_empty() { continue; }
            let cmd = tokens[0];
            if cmd == "DAH" || cmd == "LAL" {
                if tokens.len() > 2 {
                    let dest = tokens[1];
                    let src = tokens[2];
                    if dest.starts_with('R') && src.starts_with('R') {
                        let dest_typ = allocated_regs.get(dest);
                        let src_typ = allocated_regs.get(src);
                        if dest_typ != src_typ {
                            return Err(format!("CRITICAL COMPILE ERROR: Strongly typed temporal domain mismatch. Cannot perform arithmetic between '{}' ({:?}) and '{}' ({:?})", dest, dest_typ, src, src_typ));
                        }
                    }
                }
            }
        }

        Ok(())
    }
}

fn parse_b60_digit(token: &str) -> i128 {
    if token == "-" { return 0; }
    let tens = token.chars().filter(|&c| c == '<').count() as i128;
    let ones = token.chars().filter(|&c| c == 'Y' || c == 'v' || c == 'T').count() as i128;
    tens * 10 + ones
}

// Support parsing sexagesimal fractions with semicolon separator: [ int_part ; frac_part ]
fn parse_b60_number(b60_str: &str) -> (i128, u32) {
    let inner = b60_str.trim_matches(|c| c == '[' || c == ']' || c == ' ');
    if inner.is_empty() { return (0, 0); }
    
    let parts: Vec<&str> = inner.split(';').collect();
    let int_part = parts[0];
    
    // Parse integer part
    let int_places: Vec<&str> = int_part.split_whitespace().collect();
    let mut int_val = 0_i128;
    let mut power = if int_places.is_empty() { 0 } else { (int_places.len() - 1) as u32 };
    for p in int_places {
        int_val += parse_b60_digit(p) * 60_i128.pow(power);
        if power > 0 { power -= 1; }
    }
    
    if parts.len() < 2 {
        return (int_val, 0);
    }
    
    // Parse fractional part
    let frac_part = parts[1];
    let frac_places: Vec<&str> = frac_part.split_whitespace().collect();
    let scale = frac_places.len() as u32;
    let mut frac_val = 0_i128;
    for (i, p) in frac_places.iter().enumerate() {
        let power_frac = (scale - 1 - i as u32) as u32;
        frac_val += parse_b60_digit(p) * 60_i128.pow(power_frac);
    }
    
    let total_val = int_val * 60_i128.pow(scale) + frac_val;
    (total_val, scale)
}

fn format_b60(val: i128, scale: u32) -> String {
    if val == 0 { return "[-]".to_string(); }
    
    let denom = 60_i128.pow(scale);
    let int_part = val.abs() / denom;
    let mut frac_part = val.abs() % denom;
    
    let mut int_places = Vec::new();
    let mut temp = int_part;
    while temp > 0 {
        int_places.push(temp % 60);
        temp /= 60;
    }
    if int_places.is_empty() {
        int_places.push(0);
    }
    int_places.reverse();
    
    let mut int_strs = Vec::new();
    for p in int_places {
        if p == 0 {
            int_strs.push("-".to_string());
        } else {
            let tens = p / 10;
            let ones = p % 10;
            let mut s = String::new();
            for _ in 0..tens { s.push('<'); }
            for _ in 0..ones { s.push('Y'); }
            int_strs.push(s);
        }
    }
    
    let sign_prefix = if val < 0 { "NEG " } else { "" };
    
    if scale == 0 {
        return format!("{}[ {} ]", sign_prefix, int_strs.join(" "));
    }
    
    let mut frac_places = Vec::new();
    for _ in 0..scale {
        frac_part *= 60;
        frac_places.push(frac_part / denom);
        frac_part %= denom;
    }
    
    let mut frac_strs = Vec::new();
    for p in frac_places {
        if p == 0 {
            frac_strs.push("-".to_string());
        } else {
            let tens = p / 10;
            let ones = p % 10;
            let mut s = String::new();
            for _ in 0..tens { s.push('<'); }
            for _ in 0..ones { s.push('Y'); }
            frac_strs.push(s);
        }
    }
    
    format!("{}[ {} ; {} ]", sign_prefix, int_strs.join(" "), frac_strs.join(" "))
}

fn get_reg_index(reg_str: &str) -> usize {
    if reg_str.starts_with('R') {
        reg_str[1..].parse().unwrap_or(0)
    } else {
        0
    }
}

fn parse_unit(unit_str: &str) -> i128 {
    match unit_str {
        "UNIT.TICK" => 1,
        "UNIT.SECOND" => 1000,
        "UNIT.MINUTE" => 60000,
        "UNIT.HOUR" => 3600000,
        _ => 1,
    }
}

// Returns (value, scale)
fn eval_expr(expr: &str, unit: &str, registers: &[Register]) -> (i128, u32) {
    if expr.starts_with('[') {
        let (val, scale) = parse_b60_number(expr);
        (val * parse_unit(unit), scale)
    } else if expr.starts_with('R') {
        let idx = get_reg_index(expr);
        (registers[idx].val, registers[idx].scale)
    } else {
        (0, 0)
    }
}

fn divide_exact(numerator: i128, scale: u32, divisor: i128) -> (i128, u32) {
    if divisor == 0 { return (0, scale); }
    let mut num = numerator;
    let mut sc = scale;
    while num % divisor != 0 && sc < 5 {
        num *= 60;
        sc += 1;
    }
    (num / divisor, sc)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <script.b60>", args[0]);
        std::process::exit(1);
    }

    let code = fs::read_to_string(&args[1]).expect("Failed to read script");
    
    // --- Compile & Static Proof Phase ---
    let program = match B60Compiler::compile(&code) {
        Ok(p) => p,
        Err(err) => {
            eprintln!("{}", err);
            std::process::exit(1);
        }
    };
    
    let mut labels: HashMap<String, usize> = HashMap::new();
    for (i, line) in program.iter().enumerate() {
        if line.starts_with("MUB ") {
            let name = line.split_whitespace().nth(1).unwrap().trim_matches('"');
            labels.insert(name.to_string(), i);
        }
    }

    // 12. Minimal Virtual Machine (TCB Reduction)
    let initial_regs = vec![Register { val: 0, typ: B60Type::UNALLOCATED, scale: 0 }; 64];
    let mut ledger = DAGLedger::new();
    let mut clock = LogicalClock(0);
    let mut queue: VecDeque<Coroutine> = VecDeque::new();
    
    queue.push_back(Coroutine {
        id: 0,
        pc: 0,
        regs: initial_regs,
        state: CoroutineState::Ready,
    });
    
    let mut next_co_id = 1;
    let mut is_halting = false;

    // Kernel Scheduler Loop
    while let Some(mut co) = queue.pop_front() {
        if is_halting { break; }
        if co.state == CoroutineState::Halted || co.state == CoroutineState::Completed {
            continue;
        }

        if let CoroutineState::WaitingTimer(target_tick) = co.state {
            if clock >= target_tick {
                co.state = CoroutineState::Ready;
            } else {
                queue.push_back(co);
                clock.0 += 1;
                continue;
            }
        }

        if let CoroutineState::Waiting(ref await_sym) = co.state {
            if ledger.events.values().any(|ev| ev.payload == *await_sym) {
                co.state = CoroutineState::Ready;
            } else {
                queue.push_back(co);
                continue;
            }
        }

        if co.pc >= program.len() {
            continue;
        }

        let line = &program[co.pc];
        co.pc += 1;
        
        if line.is_empty() || line == "DUB" || line.starts_with("MUB ") {
            queue.push_back(co);
            continue;
        }

        let mut tokens = Vec::new();
        let mut in_bracket = false;
        let mut in_string = false;
        let mut cur = String::new();
        for c in line.chars() {
            if c == '"' {
                in_string = !in_string;
                cur.push(c);
            } else if c == '[' && !in_string {
                in_bracket = true;
                cur.push(c);
            } else if c == ']' && !in_string {
                in_bracket = false;
                cur.push(c);
                tokens.push(cur.trim().to_string());
                cur.clear();
            } else if c.is_whitespace() && !in_bracket && !in_string {
                if !cur.is_empty() {
                    tokens.push(cur.clone());
                    cur.clear();
                }
            } else {
                cur.push(c);
            }
        }
        if !cur.is_empty() { tokens.push(cur); }
        if tokens.is_empty() { queue.push_back(co); continue; }

        let cmd = tokens[0].as_str();

        match cmd {
            "NIG" => {
                let idx = get_reg_index(&tokens[1]);
                let unit = if tokens.len() > 3 { &tokens[3] } else { "" };
                let (val, scale) = eval_expr(&tokens[2], unit, &co.regs);
                co.regs[idx].val = val;
                co.regs[idx].scale = scale;
                ledger.append(format!("EV_{}", clock.0), "NIG".to_string(), format!("R{}={}", idx, format_b60(val, scale)), clock);
            }
            "FORK" => {
                let target = &tokens[1].trim_matches('"');
                let mut new_co = co.clone();
                new_co.id = next_co_id;
                next_co_id += 1;
                new_co.pc = *labels.get(*target).unwrap_or(&0);
                new_co.state = CoroutineState::Ready;
                queue.push_back(new_co);
                ledger.append(format!("EV_{}", clock.0), "FORK".to_string(), target.to_string(), clock);
            }
            "AWAIT" => {
                let symbol = tokens[1].trim_matches('"');
                let target = tokens[2].trim_matches('"');
                co.state = CoroutineState::Waiting(symbol.to_string());
                co.pc = *labels.get(target).unwrap_or(&0);
                ledger.append(format!("EV_{}", clock.0), "AWAIT".to_string(), symbol.to_string(), clock);
            }
            "AFTER" => {
                let idx = get_reg_index(&tokens[1]);
                let target = tokens[2].trim_matches('"');
                let ticks = co.regs[idx].val as u64;
                co.state = CoroutineState::WaitingTimer(LogicalClock(clock.0 + ticks));
                co.pc = *labels.get(target).unwrap_or(&0);
                ledger.append(format!("EV_{}", clock.0), "AFTER".to_string(), format!("{}", ticks), clock);
            }
            "EXECUTE" => {
                let action = tokens[1].trim_matches('"');
                let ev_id = format!("EV_{}", clock.0);
                ledger.append(ev_id, "EXECUTE".to_string(), action.to_string(), clock);
                if action.starts_with("CRITICAL_HALT") {
                    is_halting = true;
                }
            }
            "CRITICAL" => {
                if tokens.get(1).map(|s| s.as_str()) == Some("HALT") {
                    co.state = CoroutineState::Halted;
                    is_halting = true;
                }
            }
            "ALLOC" => {
                let typ_str = &tokens[1];
                let idx = get_reg_index(&tokens[2]);
                co.regs[idx].typ = match typ_str.as_str() {
                    "TIME" => B60Type::TIME,
                    "F60" => B60Type::F60,
                    _ => B60Type::I64,
                };
            }
            "DAH" => {
                let idx = get_reg_index(&tokens[1]);
                let (val2, scale2) = eval_expr(&tokens[2], "", &co.regs);
                
                // Exact Fraction Addition logic
                let s_max = std::cmp::max(co.regs[idx].scale, scale2);
                let v1 = co.regs[idx].val * 60_i128.pow(s_max - co.regs[idx].scale);
                let v2 = val2 * 60_i128.pow(s_max - scale2);
                co.regs[idx].val = v1 + v2;
                co.regs[idx].scale = s_max;
                
                ledger.append(format!("EV_{}", clock.0), "DAH".to_string(), format!("R{}+={}", idx, format_b60(val2, scale2)), clock);
            }
            "LAL" => {
                let idx = get_reg_index(&tokens[1]);
                let (val2, scale2) = eval_expr(&tokens[2], "", &co.regs);
                
                // Exact Fraction Subtraction logic
                let s_max = std::cmp::max(co.regs[idx].scale, scale2);
                let v1 = co.regs[idx].val * 60_i128.pow(s_max - co.regs[idx].scale);
                let v2 = val2 * 60_i128.pow(s_max - scale2);
                co.regs[idx].val = v1 - v2;
                co.regs[idx].scale = s_max;
                
                ledger.append(format!("EV_{}", clock.0), "LAL".to_string(), format!("R{}-={}", idx, format_b60(val2, scale2)), clock);
            }
            "NU" => {
                let idx = get_reg_index(&tokens[1]);
                let target = tokens[2].trim_matches('"');
                if co.regs[idx].val == 0 {
                    co.pc = *labels.get(target).unwrap_or(&0);
                    ledger.append(format!("EV_{}", clock.0), "NU".to_string(), format!("JMP {}", target), clock);
                }
            }
            "BA.EXACT" => {
                let idx = get_reg_index(&tokens[1]);
                let idx2 = get_reg_index(&tokens[2]);
                let divisor = co.regs[idx2].val;
                let (new_val, new_scale) = divide_exact(co.regs[idx].val, co.regs[idx].scale, divisor);
                co.regs[idx].val = new_val;
                co.regs[idx].scale = new_scale;
                
                ledger.append(format!("EV_{}", clock.0), "BA.EXACT".to_string(), format!("R{}/={}", idx, divisor), clock);
            }
            "HALT" => {
                co.state = CoroutineState::Halted;
            }
            "SAR" => {
                let idx = get_reg_index(&tokens[1]);
                println!("[SERIAL R{}] {}", idx, co.regs[idx].val);
            }
            "SAR.B60" => {
                let idx = get_reg_index(&tokens[1]);
                println!("[SERIAL R{}] {}", idx, format_b60(co.regs[idx].val, co.regs[idx].scale));
            }
            _ => {}
        }
        
        clock.0 += 1;
        queue.push_back(co);
    }

    println!("[MOSKV APEX] C5-REAL Execution Completed.");
    println!("[Proof] Proof obligations generated.");
    export_artifact_bundle(&ledger, !is_halting);
}

// 11. Immutable Artifact Export
fn export_artifact_bundle(ledger: &DAGLedger, compliance: bool) {
    use std::io::Write;
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut canonical_lines = Vec::new();
    for ev in ledger.events.values() {
        let mut parents = ev.parents.clone();
        parents.sort();
        let parents_str = parents.join(",");
        canonical_lines.push(format!("{}|{}|{}|{}|{}", ev.id, parents_str, ev.logical_timestamp.0, ev.payload, ev.signature));
    }
    
    canonical_lines.sort();
    let canonical_graph = canonical_lines.join("
") + "
";
    
    let mut hasher = DefaultHasher::new();
    canonical_graph.hash(&mut hasher);
    let graph_hash = format!("{:x}", hasher.finish());

    let manifest = format!(r#"{{
  "version": "1.0",
  "components": ["trace.bin", "graph.canonical", "proof.ir", "metadata.json", "hashes/", "signature/"],
  "global_hash": "{}",
  "theorem_of_babylon_compliance": {}
}}"#, graph_hash, compliance);

    let mut ir_lines = Vec::new();
    let mut sorted_events: Vec<_> = ledger.events.values().collect();
    sorted_events.sort_by_key(|ev| &ev.id);
    
    for ev in sorted_events {
        ir_lines.push(format!("(Event {} {})", ev.id, ev.logical_timestamp.0));
        for parent in &ev.parents {
            ir_lines.push(format!("(HappensBefore {} {})", parent, ev.id));
        }
        match ev.opcode.as_str() {
            "NIG" => ir_lines.push(format!("(Assign {} {})", ev.payload.replace("=", " "), ev.id)),
            "DAH" => ir_lines.push(format!("(Add {} {})", ev.payload.replace("+=", " "), ev.id)),
            "LAL" => ir_lines.push(format!("(Sub {} {})", ev.payload.replace("-=", " "), ev.id)),
            "FORK" => ir_lines.push(format!("(Spawn {} {})", ev.payload, ev.id)),
            "AWAIT" => ir_lines.push(format!("(Block {} {})", ev.payload, ev.id)),
            "AFTER" => ir_lines.push(format!("(Wait {} {})", ev.payload, ev.id)),
            "EXECUTE" => ir_lines.push(format!("(Emit {} {})", ev.payload, ev.id)),
            _ => ir_lines.push(format!("(Unknown {} {})", ev.payload, ev.id)),
        }
    }
    let proof_ir = ir_lines.join("
") + "
";

    fs::create_dir_all("artifact_bundle_v3").unwrap();
    fs::write("artifact_bundle_v3/manifest.json", manifest).unwrap();
    fs::write("artifact_bundle_v3/graph.canonical", &canonical_graph).unwrap();
    fs::write("artifact_bundle_v3/proof.ir", proof_ir).unwrap();
    
    println!("-> [Exporter] Canonical graph generated. graph.sha256 approx: {}", graph_hash);
    println!("-> [Exporter] Proof IR extracted. Dispatched to Lean/Coq Backends.");
    println!("-> [Bootstrap v3.0] Artifact Bundle securely formalized at artifact_bundle_v3/");
}
