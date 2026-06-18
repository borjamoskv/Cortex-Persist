use std::collections::HashMap;
use std::env;
use std::fs;
use std::thread;
use std::time::Duration;

#[derive(Clone, Debug, PartialEq)]
enum B60Type {
    I64,
    TIME,
    F60,
    UNALLOCATED,
}

#[derive(Clone, Debug)]
struct Register {
    val: i64,
    typ: B60Type,
}

fn parse_b60_digit(token: &str) -> i64 {
    if token == "-" { return 0; }
    let tens = token.chars().filter(|&c| c == '<').count() as i64;
    let ones = token.chars().filter(|&c| c == 'Y' || c == 'v' || c == 'T').count() as i64;
    tens * 10 + ones
}

fn parse_b60_number(b60_str: &str) -> i64 {
    let inner = b60_str.trim_matches(|c| c == '[' || c == ']' || c == ' ');
    if inner.is_empty() { return 0; }
    let places: Vec<&str> = inner.split_whitespace().collect();
    let mut total = 0;
    let mut power = (places.len() - 1) as u32;
    for p in places {
        total += parse_b60_digit(p) * 60_i64.pow(power);
        if power > 0 { power -= 1; }
    }
    total
}

fn format_b60(mut val: i64) -> String {
    if val == 0 { return "[-]".to_string(); }
    let mut places = Vec::new();
    while val > 0 {
        places.push(val % 60);
        val /= 60;
    }
    places.reverse();
    let mut out = Vec::new();
    for p in places {
        if p == 0 {
            out.push("-".to_string());
        } else {
            let tens = p / 10;
            let ones = p % 10;
            let mut s = String::new();
            for _ in 0..tens { s.push('<'); }
            for _ in 0..ones { s.push('Y'); }
            out.push(s);
        }
    }
    format!("[ {} ]", out.join(" "))
}

fn get_reg_index(reg_str: &str) -> usize {
    if reg_str.starts_with('R') {
        reg_str[1..].parse().unwrap_or(0)
    } else {
        0
    }
}

fn eval_expr(expr: &str, registers: &[Register]) -> i64 {
    if expr.starts_with('[') {
        parse_b60_number(expr)
    } else if expr.starts_with('R') {
        let idx = get_reg_index(expr);
        registers[idx].val
    } else {
        0
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <script.b60>", args[0]);
        std::process::exit(1);
    }

    let code = fs::read_to_string(&args[1]).expect("Failed to read script");
    let lines: Vec<&str> = code.lines().map(|l| l.split('#').next().unwrap().trim()).collect();
    
    let mut registers = vec![Register { val: 0, typ: B60Type::UNALLOCATED }; 64];
    let mut labels: HashMap<String, usize> = HashMap::new();

    for (i, line) in lines.iter().enumerate() {
        if line.starts_with("MUB ") {
            let name = line.split_whitespace().nth(1).unwrap();
            labels.insert(name.to_string(), i);
        }
    }

    let mut pc = 0;
    while pc < lines.len() {
        let line = lines[pc];
        if line.is_empty() || line == "DUB" || line.starts_with("MUB ") {
            pc += 1;
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
        if tokens.is_empty() { pc += 1; continue; }

        let cmd = tokens[0].as_str();
        match cmd {
            "ALLOC" => {
                let typ_str = &tokens[1];
                let idx = get_reg_index(&tokens[2]);
                registers[idx].typ = match typ_str.as_str() {
                    "TIME" => B60Type::TIME,
                    "F60" => B60Type::F60,
                    _ => B60Type::I64,
                };
            }
            "NIG" => {
                let idx = get_reg_index(&tokens[1]);
                registers[idx].val = eval_expr(&tokens[2], &registers);
            }
            "AFTER" => {
                let idx = get_reg_index(&tokens[1]);
                let secs = registers[idx].val as u64;
                println!("[MOSKV CLOCK] Sleeping for {} base units...", secs);
                thread::sleep(Duration::from_secs(secs));
                if let Some(&target) = labels.get(&tokens[2]) {
                    pc = target;
                    continue;
                }
            }
            "EXECUTE" => {
                let action = tokens[1].trim_matches('"');
                println!("[MOSKV LEDGER DISPATCH] ⚡ {} ", action);
            }
            "SAR" => {
                let val = eval_expr(&tokens[1], &registers);
                println!("SAR (DEC): {}", val);
            }
            "SAR.B60" => {
                let val = eval_expr(&tokens[1], &registers);
                println!("SAR (B60): {}", format_b60(val));
            }
            "HALT" => {
                break;
            }
            _ => {}
        }
        pc += 1;
    }
}
