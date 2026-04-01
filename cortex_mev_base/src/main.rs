mod alloy_client;
mod types;

use std::env;
use tracing::{info, Level};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Configurar Tracing agresivo para O(1) logging
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();

    info!("Iniciando Capital-Extractor-Omega: Base Latency Engine (Rust/Huff)");

    // URL WebSocket (Default: Pública de Base de ejemplo, aunque se exige Nodo Propio para Latency)
    let ws_url = env::var("BASE_WS_URL").unwrap_or_else(|_| "wss://base-mainnet.public.blastapi.io".to_string());

    // Bloqueo principal en la subscripción de la red
    match alloy_client::start_latency_engine(&ws_url).await {
        Ok(_) => info!("Engine cerrado por final de ciclo de mercado."),
        Err(e) => tracing::error!("Error Fatal en Engine: {:?}", e),
    }

    Ok(())
}
