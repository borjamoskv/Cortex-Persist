use num_bigint::BigInt;
use num_integer::Integer;
use num_traits::{One, Pow, ToPrimitive, Zero};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, VecDeque};
use std::env;
use std::fs;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
enum B60Type {
    I64,
    Time,
    F60,
    Unallocated,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct F60 {
    num: BigInt,
    scale: u32,
}

impl F60 {
    fn new(num: BigInt, scale: u32) -> Self {
        let mut f = F60 { num, scale };
        f.reduce();
        f
    }

    fn reduce(&mut self) {
        if self.num.is_zero() {
            self.scale = 0;
            return;
        }
        let base = BigInt::from(60_u64).pow(self.scale);
        let g = self.num.gcd(&base);
        if g > BigInt::one() {
            self.num /= &g;
            let mut g_temp = g;
            while (&g_temp % 60u64).is_zero() && self.scale > 0 {
                g_temp /= 60u64;
                self.scale -= 1;
            }
        }
    }

}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct Register {
    val: F60,
    typ: B60Type,
}

#[derive(Clone, Debug)]
enum CoroutineState {
    Ready,
    Waiting(String),   // AWAIT symbol
    WaitingTimer(u64), // AFTER tick
    Running,
    Completed,
    Halted,
}

#[derive(Clone, Debug)]
struct Coroutine {
    #[allow(dead_code)]
    id: usize,
    pc: usize,
    state: CoroutineState,
    r: Vec<Register>,
}

#[derive(Serialize)]
struct OpTrace {
    action: String,
    symbol: String,
    status: String,
}

#[derive(Serialize)]
struct F60Delta {
    cell_id: String,
    delta_numerator: String,
    delta_scale: u32,
}

#[derive(Serialize)]
struct TickSequence {
    tick: u64,
    opcode: String,
    registers_snapshot: HashMap<String, String>,
}

#[derive(Serialize)]
struct ExportSchema {
    initial_state_hash: String,
    tick_sequence: Vec<TickSequence>,
    op_trace: Vec<OpTrace>,
    f60_deltas: Vec<F60Delta>,
    energy_vector: Vec<String>,
    replay_hash: String,
    theorem_prover_payload: String,
}

struct Machine {
    q: VecDeque<Coroutine>,
    l: Vec<TickSequence>,
    op_trace: Vec<OpTrace>,
    f60_deltas: Vec<F60Delta>,
    c: u64, // Clock
    labels: HashMap<String, usize>,
    lines: Vec<String>,
    next_cid: usize,
    emitted_events: std::collections::HashSet<String>,
}

fn parse_b60_digit(token: &str) -> i64 {
    if token == "-" {
        return 0;
    }
    let tens = token.chars().filter(|&c| c == '<').count() as i64;
    let ones = token
        .chars()
        .filter(|&c| c == 'Y' || c == 'v' || c == 'T')
        .count() as i64;
    tens * 10 + ones
}

fn parse_b60_number(b60_str: &str) -> F60 {
    let inner = b60_str.trim_matches(|c| c == '[' || c == ']' || c == ' ');
    if inner.is_empty() {
        return F60::new(BigInt::zero(), 0);
    }
    let places: Vec<&str> = inner.split_whitespace().collect();
    let mut total = BigInt::zero();
    let mut power = (places.len() - 1) as u32;
    for p in places {
        total += BigInt::from(parse_b60_digit(p)) * BigInt::from(60u64).pow(power);
        power = power.saturating_sub(1);
    }
    F60::new(total, 0)
}

fn get_reg_index(reg_str: &str) -> usize {
    if let Some(stripped) = reg_str.strip_prefix('R') {
        stripped.parse().unwrap_or(0)
    } else {
        0
    }
}

impl Machine {
    fn eval_expr(&self, expr: &str, r: &[Register]) -> F60 {
        if expr.starts_with('[') {
            parse_b60_number(expr)
        } else if expr.starts_with('R') {
            let idx = get_reg_index(expr);
            r[idx].val.clone()
        } else if expr == "UNIT.HOUR" {
            F60::new(BigInt::from(3600u64), 0)
        } else if expr == "UNIT.MINUTE" {
            F60::new(BigInt::from(60u64), 0)
        } else {
            F60::new(BigInt::zero(), 0)
        }
    }

    fn critical_halt(&mut self, reason: &str) {
        println!("[ MOSKV KERNEL ] CRITICAL HALT: {}", reason);
        self.export_artifact();
        std::process::exit(1);
    }

    fn export_artifact(&self) {
        println!("[ MOSKV KERNEL ] CAUSAL SNAPSHOT -> ARTIFACT EXPORT");
        let mut hasher = Sha256::new();
        hasher.update(b"BABYLON-60-INIT");
        let initial_res = hasher.finalize();
        let initial_hash: String = initial_res.iter().map(|b| format!("{:02x}", b)).collect();

        let mut hasher2 = Sha256::new();
        hasher2.update(self.c.to_be_bytes());
        let replay_res = hasher2.finalize();
        let replay_hash: String = replay_res.iter().map(|b| format!("{:02x}", b)).collect();

        let artifact = ExportSchema {
            initial_state_hash: initial_hash,
            tick_sequence: self
                .l
                .iter()
                .map(|t| TickSequence {
                    tick: t.tick,
                    opcode: t.opcode.clone(),
                    registers_snapshot: t.registers_snapshot.clone(),
                })
                .collect(),
            op_trace: self
                .op_trace
                .iter()
                .map(|o| OpTrace {
                    action: o.action.clone(),
                    symbol: o.symbol.clone(),
                    status: o.status.clone(),
                })
                .collect(),
            f60_deltas: self
                .f60_deltas
                .iter()
                .map(|f| F60Delta {
                    cell_id: f.cell_id.clone(),
                    delta_numerator: f.delta_numerator.clone(),
                    delta_scale: f.delta_scale,
                })
                .collect(),
            energy_vector: vec!["EXERGY: 1.0".to_string()],
            replay_hash,
            theorem_prover_payload: "inductive B60State where ...".to_string(),
        };

        let json = serde_json::to_string_pretty(&artifact).unwrap();
        fs::write("proof_artifact.json", json).unwrap();
        println!("[ MOSKV KERNEL ] Escrito a proof_artifact.json");
    }

    fn run(&mut self) {
        while !self.q.is_empty() {
            let mut coro = self.q.pop_front().unwrap();

            match coro.state {
                CoroutineState::Completed | CoroutineState::Halted => continue,
                CoroutineState::Waiting(ref sym) => {
                    if self.emitted_events.contains(sym) {
                        coro.state = CoroutineState::Ready;
                    } else {
                        self.q.push_back(coro);
                        self.c += 1;
                        continue;
                    }
                }
                CoroutineState::WaitingTimer(target_tick) => {
                    if self.c >= target_tick {
                        coro.state = CoroutineState::Ready;
                    } else {
                        self.q.push_back(coro);
                        self.c += 1;
                        continue;
                    }
                }
                _ => {}
            }

            coro.state = CoroutineState::Running;

            if coro.pc >= self.lines.len() {
                coro.state = CoroutineState::Completed;
                continue;
            }

            let line = self.lines[coro.pc].trim().to_string();
            if line.is_empty() || line == "DUB" || line.starts_with("MUB ") || line.starts_with('#')
            {
                coro.pc += 1;
                coro.state = CoroutineState::Ready;
                self.q.push_back(coro);
                self.c += 1;
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
            if !cur.is_empty() {
                tokens.push(cur);
            }
            if tokens.is_empty() {
                coro.pc += 1;
                coro.state = CoroutineState::Ready;
                self.q.push_back(coro);
                continue;
            }

            let cmd = tokens[0].as_str();
            match cmd {
                "ALLOC" => {
                    let typ_str = &tokens[1];
                    let idx = get_reg_index(&tokens[2]);
                    coro.r[idx].typ = match typ_str.as_str() {
                        "TIME" => B60Type::Time,
                        "F60" => B60Type::F60,
                        _ => B60Type::I64,
                    };
                }
                "NIG" => {
                    let idx = get_reg_index(&tokens[1]);
                    coro.r[idx].val = self.eval_expr(&tokens[2], &coro.r);
                    if tokens.len() > 3 {
                        let mult = self.eval_expr(&tokens[3], &coro.r);
                        coro.r[idx].val.num *= mult.num;
                    }
                }
                "BA.EXACT" => {
                    let idx1 = get_reg_index(&tokens[1]);
                    let val2 = self.eval_expr(&tokens[2], &coro.r);

                    if val2.num.is_zero() {
                        self.critical_halt("DIVIDE_BY_ZERO");
                    }

                    let mut num = coro.r[idx1].val.num.clone();
                    let mut scale = coro.r[idx1].val.scale;

                    while (&num % &val2.num) != BigInt::zero() {
                        num *= 60u64;
                        scale += 1;
                        if scale > 20 {
                            // Saturation limit
                            self.critical_halt("FALSATION_ERROR: TRUNCATION (Blowup de Numerador excedió límite de Escala F60)");
                        }
                    }

                    coro.r[idx1].val = F60::new(num / val2.num, scale);
                }
                "FORK" => {
                    let label = &tokens[1];
                    if let Some(&target) = self.labels.get(label) {
                        let new_coro = Coroutine {
                            id: self.next_cid,
                            pc: target,
                            state: CoroutineState::Ready,
                            r: coro.r.clone(),
                        };
                        self.next_cid += 1;
                        self.q.push_back(new_coro);

                        self.op_trace.push(OpTrace {
                            action: "FORK".to_string(),
                            symbol: label.clone(),
                            status: "RESOLVED".to_string(),
                        });
                    }
                }
                "AFTER" => {
                    let idx = get_reg_index(&tokens[1]);
                    let ticks = coro.r[idx].val.num.to_u64().unwrap_or(0);
                    let label = &tokens[2];
                    if let Some(&target) = self.labels.get(label) {
                        coro.state = CoroutineState::WaitingTimer(self.c + ticks);
                        coro.pc = target;
                        self.q.push_back(coro);
                        self.c += 1;
                        continue;
                    }
                }
                "AWAIT" => {
                    let sym = tokens[1].trim_matches('"').to_string();
                    let label = &tokens[2];
                    if let Some(&target) = self.labels.get(label) {
                        coro.state = CoroutineState::Waiting(sym.clone());
                        coro.pc = target;
                        self.op_trace.push(OpTrace {
                            action: "AWAIT".to_string(),
                            symbol: sym.clone(),
                            status: "PENDING".to_string(),
                        });
                        self.q.push_back(coro);
                        self.c += 1;
                        continue;
                    }
                }
                "EXECUTE" => {
                    let action = tokens[1].trim_matches('"').to_string();
                    println!("[MOSKV LEDGER DISPATCH] ⚡ {} (Tick: {})", action, self.c);
                    self.emitted_events.insert(action.clone());
                    self.op_trace.push(OpTrace {
                        action: "EXECUTE".to_string(),
                        symbol: action.clone(),
                        status: "RESOLVED".to_string(),
                    });
                }
                "SAR.B60" => {
                    let idx = get_reg_index(&tokens[1]);
                    println!(
                        "SAR (B60): num={} scale={}",
                        coro.r[idx].val.num, coro.r[idx].val.scale
                    );
                }
                "GIN" => {
                    let label = &tokens[1];
                    if let Some(&target) = self.labels.get(label) {
                        coro.pc = target;
                        coro.state = CoroutineState::Ready;
                        self.q.push_back(coro);
                        self.c += 1;
                        continue;
                    }
                }
                "HALT" => {
                    coro.state = CoroutineState::Halted;
                    self.q.push_back(coro);
                    self.c += 1;
                    continue;
                }
                _ => {}
            }

            let mut snap = HashMap::new();
            snap.insert("PC".to_string(), coro.pc.to_string());
            self.l.push(TickSequence {
                tick: self.c,
                opcode: line.clone(),
                registers_snapshot: snap,
            });

            coro.pc += 1;
            coro.state = CoroutineState::Ready;
            self.q.push_back(coro);
            self.c += 1;
        }

        self.export_artifact();
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <script.b60>", args[0]);
        std::process::exit(1);
    }

    let code = fs::read_to_string(&args[1]).expect("Failed to read script");
    let lines: Vec<String> = code.lines().map(|l| l.trim().to_string()).collect();

    let mut labels = HashMap::new();
    for (i, line) in lines.iter().enumerate() {
        if line.starts_with("MUB ") {
            let name = line.split_whitespace().nth(1).unwrap();
            labels.insert(name.to_string(), i);
        }
    }

    let initial_r = vec![
        Register {
            val: F60::new(BigInt::zero(), 0),
            typ: B60Type::Unallocated
        };
        64
    ];
    let root_coro = Coroutine {
        id: 0,
        pc: 0,
        state: CoroutineState::Ready,
        r: initial_r,
    };

    let mut machine = Machine {
        q: VecDeque::from(vec![root_coro]),
        l: Vec::new(),
        op_trace: Vec::new(),
        f60_deltas: Vec::new(),
        c: 0,
        labels,
        lines,
        next_cid: 1,
        emitted_events: std::collections::HashSet::new(),
    };

    machine.run();
}
