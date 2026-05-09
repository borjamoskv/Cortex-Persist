use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::path::Path;
use std::time::Instant;
use chrono::Local;

#[derive(Serialize, Deserialize, Clone, Debug)]
struct ContractMatch {
    file_path: String,
    contract_name: String,
    functions_count: usize,
}

fn walk_dir(dir: &Path, results: &mut Vec<ContractMatch>) {
    if dir.is_dir() {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    walk_dir(&path, results);
                } else if path.extension().and_then(|s| s.to_str()) == Some("sol") {
                    if let Ok(content) = fs::read_to_string(&path) {
                        let contract_count = content.matches("contract ").count();
                        if contract_count > 0 {
                            let functions_count = content.matches("function ").count();
                            
                            let mut contract_name = "Unknown".to_string();
                            if let Some(idx) = content.find("contract ") {
                                let remainder = &content[idx + 9..];
                                if let Some(end_idx) = remainder.find(|c: char| !c.is_alphanumeric() && c != '_') {
                                    contract_name = remainder[..end_idx].to_string();
                                }
                            }

                            results.push(ContractMatch {
                                file_path: path.to_string_lossy().into_owned(),
                                contract_name,
                                functions_count,
                            });
                        }
                    }
                }
            }
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let t0 = Instant::now();
    println!("[{}] [SYSTEM] [MOSKV-AST-RS] Iniciando Motor C5-REAL (Offline)...", Local::now().format("%H:%M:%S%.3f"));
    
    let args: Vec<String> = env::args().collect();
    let target_dir = if args.len() > 1 {
        &args[1]
    } else {
        "."
    };

    println!("[{}] [AST] Escaneando directorio: {}", Local::now().format("%H:%M:%S%.3f"), target_dir);

    let mut results = Vec::new();
    walk_dir(Path::new(target_dir), &mut results);

    let serialized = serde_json::to_string_pretty(&results)?;
    
    let home = env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let output_path = format!("{}/10_PROJECTS/cortex-persist/engine-rs/offline_ast_matrix.json", home);
    
    if let Some(parent) = Path::new(&output_path).parent() {
        fs::create_dir_all(parent)?;
    }
    
    fs::write(&output_path, serialized)?;

    println!("[{}] [SYSTEM] Escaneo de Hardware concluido. {} contratos encontrados.", Local::now().format("%H:%M:%S%.3f"), results.len());
    println!("[{}] [SUCCESS] Matriz de Falsación guardada en: {}", Local::now().format("%H:%M:%S%.3f"), output_path);
    println!("[{}] [SYSTEM] Operación Bare-Metal finalizada en {:.2} ms (Zero Thermal Noise).", Local::now().format("%H:%M:%S%.3f"), t0.elapsed().as_secs_f64() * 1000.0);

    Ok(())
}
