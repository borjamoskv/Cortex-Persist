use futures_util::SinkExt;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::fs;
use std::sync::Arc;
use std::time::Instant;
use tokio::net::TcpListener;
use tokio::sync::{broadcast, Mutex, Semaphore};
use tokio_tungstenite::accept_async;

const CONCURRENCY_LIMIT: usize = 500;
const TOTAL_AGENTS: usize = 10000;
const WS_PORT: &str = "8081";

#[derive(Serialize, Deserialize, Clone, Debug)]
struct Target {
    name: String,
    url: String,
    best_rtt: f64,
    winning_agent: i32,
    block: String,
}

#[derive(Serialize, Clone, Debug)]
struct TelemetryFrame {
    agent_id: usize,
    rtt: f64,
    target: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let t0 = Instant::now();
    println!("[{}] [SYSTEM] [MOSKV-10k-RS] Iniciando Matriz Atómica (C5-REAL)...", chrono::Local::now().format("%H:%M:%S%.3f"));
    
    // ── WebSocket Server Setup ──
    let (tx, _rx) = broadcast::channel::<TelemetryFrame>(1024);
    let tx_ws = tx.clone();

    tokio::spawn(async move {
        let addr = format!("127.0.0.1:{}", WS_PORT);
        let listener = TcpListener::bind(&addr).await.expect("Failed to bind WS port");
        println!("[{}] [WS] Servidor de Telemetría activo en ws://{}", chrono::Local::now().format("%H:%M:%S%.3f"), addr);

        while let Ok((stream, _)) = listener.accept().await {
            let tx_clone = tx_ws.clone();
            tokio::spawn(async move {
                if let Ok(mut ws_stream) = accept_async(stream).await {
                    println!("[{}] [WS] Cliente conectado al dashboard.", chrono::Local::now().format("%H:%M:%S%.3f"));
                    let mut rx = tx_clone.subscribe();
                    while let Ok(msg) = rx.recv().await {
                        let json_msg = serde_json::to_string(&msg).unwrap();
                        if ws_stream.send(tokio_tungstenite::tungstenite::Message::Text(json_msg.into())).await.is_err() {
                            break;
                        }
                    }
                }
            });
        }
    });

    // ── Swarm Setup ──
    let targets = vec![
        Target { name: "Ethereum-Cloudflare".to_string(), url: "https://cloudflare-eth.com".to_string(), best_rtt: f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
        Target { name: "Ethereum-Public".to_string(), url: "https://rpc.ankr.com/eth".to_string(), best_rtt: f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
        Target { name: "Base-Public".to_string(), url: "https://mainnet.base.org".to_string(), best_rtt: f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
        Target { name: "Arbitrum-Public".to_string(), url: "https://arb1.arbitrum.io/rpc".to_string(), best_rtt: f64::INFINITY, winning_agent: -1, block: "N/A".to_string() },
    ];

    let shared_targets = Arc::new(Mutex::new(targets));
    let client = Client::builder()
        .pool_max_idle_per_host(CONCURRENCY_LIMIT)
        .timeout(std::time::Duration::from_millis(2000))
        .build()?;

    let semaphore = Arc::new(Semaphore::new(CONCURRENCY_LIMIT));
    let mut handles = vec![];

    let payload = json!({
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    });

    println!("[{}] [SWARM] Liberando Legión de {} Agentes...", chrono::Local::now().format("%H:%M:%S%.3f"), TOTAL_AGENTS);

    for agent_id in 0..TOTAL_AGENTS {
        let client_clone = client.clone();
        let payload_clone = payload.clone();
        let sem_clone = semaphore.clone();
        let shared_targets_clone = shared_targets.clone();
        let tx_clone = tx.clone();

        handles.push(tokio::spawn(async move {
            let _permit = match sem_clone.acquire().await {
                Ok(p) => p,
                Err(_) => return,
            };

            let target_idx = agent_id % 4;
            let (url, target_name) = {
                let targets_lock = shared_targets_clone.lock().await;
                (targets_lock[target_idx].url.clone(), targets_lock[target_idx].name.clone())
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

                    // Emitir telemetría
                    let _ = tx_clone.send(TelemetryFrame {
                        agent_id,
                        rtt,
                        target: target_name,
                    });

                    if agent_id % 1000 == 0 {
                        println!("[{}] [L-STRIKE] Agent-{} [ATOMIC] RTT: {:.2}ms", chrono::Local::now().format("%H:%M:%S%.3f"), agent_id, rtt);
                    }
                }
            }
        }));
    }

    futures::future::join_all(handles).await;

    let final_targets = shared_targets.lock().await;
    let serialized = serde_json::to_string_pretty(&*final_targets)?;
    
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let path = format!("{}/Cortex-Persist/engine-c5/mev_rpc_routing.json", home);
    fs::write(&path, serialized)?;

    println!("[{}] [SYSTEM] Asalto concluido. Exergía recolectada.", chrono::Local::now().format("%H:%M:%S%.3f"));
    println!("[{}] [SUCCESS] Matriz inyectada en: {}", chrono::Local::now().format("%H:%M:%S%.3f"), path);
    println!("[{}] [SYSTEM] Operación finalizada en {:.2} segundos.", chrono::Local::now().format("%H:%M:%S%.3f"), t0.elapsed().as_secs_f64());

    Ok(())
}
