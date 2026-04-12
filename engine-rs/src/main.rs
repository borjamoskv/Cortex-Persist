use futures::future::join_all;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::fs;
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::Mutex;

const CONCURRENCY_LIMIT: usize = 500;
const TOTAL_AGENTS: usize = 10000;

#[derive(Serialize, Deserialize, Clone)]
struct Target {
    name: String,
    url: String,
    best_rtt: f64,
    winning_agent: i32,
    block: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let t0 = Instant::now();
    println!("[{}] [SYSTEM] [MOSKV-10k-RS] Iniciando Matriz Atómica (X18-REAL)...", chrono::Local::now().format("%H:%M:%S%.3f"));
    println!("[{}] [SWARM] Liberando Legión Bare-Metal de {} Agentes en TCP/UDP crudo.", chrono::Local::now().format("%H:%M:%S%.3f"), TOTAL_AGENTS);

    let targets = vec![
        Target { name: "Ethereum-Cloudflare".to_string(), url: "https://cloudflare-eth.com".to_string(), best_rtt: std::f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
        Target { name: "Ethereum-Public".to_string(), url: "https://rpc.ankr.com/eth".to_string(), best_rtt: std::f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
        Target { name: "Base-Public".to_string(), url: "https://mainnet.base.org".to_string(), best_rtt: std::f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
        Target { name: "Arbitrum-Public".to_string(), url: "https://arb1.arbitrum.io/rpc".to_string(), best_rtt: std::f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
    ];

    let shared_targets = Arc::new(Mutex::new(targets));
    
    // Pooling is aggressive by default in Reqwest (hyper underneath)
    let client = Client::builder()
        .pool_max_idle_per_host(CONCURRENCY_LIMIT)
        .timeout(std::time::Duration::from_millis(2000))
        .build()?;

    let semaphore = Arc::new(tokio::sync::Semaphore::new(CONCURRENCY_LIMIT));
    let mut handles = vec![];

    let payload = json!({
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    });

    for agent_id in 0..TOTAL_AGENTS {
        let client_clone = client.clone();
        let payload_clone = payload.clone();
        let sem_clone = semaphore.clone();
        let shared_targets_clone = shared_targets.clone();

        handles.push(tokio::spawn(async move {
            let _permit = match sem_clone.acquire().await {
                Ok(p) => p,
                Err(_) => return,
            };

            // Target mapping logic
            let target_idx = agent_id % 4;
            let url = {
                let targets_lock = shared_targets_clone.lock().await;
                targets_lock[target_idx].url.clone()
            };

            let start = Instant::now();
            if let Ok(res) = client_clone.post(&url).json(&payload_clone).send().await {
                if res.status().is_success() {
                    let rtt = start.elapsed().as_secs_f64() * 1000.0;
                    if let Ok(resp_json) = res.json::<serde_json::Value>().await {
                        let block = resp_json["result"].as_str().unwrap_or("N/A").to_string();
                        
                        let mut targets_lock = shared_targets_clone.lock().await;
                        if rtt < targets_lock[target_idx].best_rtt {
                            targets_lock[target_idx].best_rtt = rtt;
                            targets_lock[target_idx].winning_agent = agent_id as i32;
                            targets_lock[target_idx].block = block;
                        }
                    }
                    if agent_id % 1000 == 0 {
                        println!("[{}] [L-STRIKE] Agent-{} [ATOMIC] RTT: {:.2}ms", chrono::Local::now().format("%H:%M:%S%.3f"), agent_id, rtt);
                    }
                }
            }
        }));
    }

    join_all(handles).await;

    let final_targets = shared_targets.lock().await;
    let serialized = serde_json::to_string_pretty(&*final_targets)?;
    
    // Fallback to homedir expansion directly locally.
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let path = format!("{}/Cortex-Persist/engine-c5/mev_rpc_routing.json", home);
    
    fs::write(&path, serialized)?;

    println!("[{}] [SYSTEM] Asalto de Hardware concluido.", chrono::Local::now().format("%H:%M:%S%.3f"));
    for target in final_targets.iter() {
        println!("[EXERGY] -> {} | Mínimo RTT: {:.2}ms (Bajo control del Agent-{})", target.name, target.best_rtt, target.winning_agent);
    }

    println!("[{}] [SUCCESS] Matriz TCP inyectada en: {}", chrono::Local::now().format("%H:%M:%S%.3f"), path);
    println!("[{}] [SYSTEM] Operación Bare-Metal finalizada en {:.2} segundos.", chrono::Local::now().format("%H:%M:%S%.3f"), t0.elapsed().as_secs_f64());

    Ok(())
}
