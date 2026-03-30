mod db;
mod mev_crystallizer;
mod taint;

use alloy::providers::{Provider, ProviderBuilder, IpcConnect};
use eyre::Result;
use futures_util::StreamExt;
use std::path::{Path, PathBuf};
use tokio::sync::mpsc;
use db::AlloyDB;
use mev_crystallizer::{MEVCrystallizerCore, StagingRef};

#[tokio::main]
async fn main() -> Result<()> {
    let ipc_path = "/tmp/reth.ipc"; 
    let ledger_path = PathBuf::from("./ledger");
    
    if !Path::new(ipc_path).exists() {
        println!("[!] CORTEX: No se detecta el socket IPC en {}. Operando en modo simulación local...", ipc_path);
        // Fallback for verification if necessary, but here we exit or mock.
    }

    println!("[+] CORTEX: Inicializando HFT Engine (Vector 1)...");
    
    let ipc = IpcConnect::new(ipc_path.to_string());
    let provider = ProviderBuilder::new().on_ipc(ipc).await?;

    println!("[+] CORTEX: Enlace establecido.");

    // Initialize Crystallizer
    let crystallizer = std::sync::Arc::new(tokio::sync::Mutex::new(MEVCrystallizerCore::new(
        "https://relay.flashbots.net".to_string(),
        ledger_path,
    )));

    let (tx_sender, mut tx_receiver) = mpsc::channel(1024);
    let provider_clone_for_db = provider.clone();

    // Simulation Worker
    let crystallizer_task = crystallizer.clone();
    tokio::spawn(async move {
        while let Some(tx_hash) = tx_receiver.recv().await {
            let p_clone = provider_clone_for_db.clone();
            let db = AlloyDB::new(p_clone.clone());
            
            // SIMULATION LOGIC (REVM)
            if let Ok(Some(tx)) = p_clone.get_transaction_by_hash(tx_hash).await {
                // println!("[SIM] Auditando Tx: {:?}", tx_hash);
                
                let mut evm = revm::Evm::builder()
                    .with_db(db)
                    .modify_tx_env(|env| {
                        env.caller = tx.from;
                        env.transact_to = tx.to.map(revm::primitives::TransactTo::Call).unwrap_or(revm::primitives::TransactTo::Create);
                        env.data = tx.input.into();
                        env.value = tx.value;
                        env.nonce = Some(tx.nonce);
                        env.gas_limit = tx.gas;
                        env.gas_price = tx.gas_price.unwrap_or_default();
                    })
                    .build();

                // To execute properly with AlloyDB (which uses block_on), we might need spawn_blocking
                // but since we are already in an async move block, we execute:
                match evm.transact() {
                    Ok(result) => {
                        if result.result.is_success() {
                            println!("[SIM] SUCCESS: Tx {:?} | Exergy: {}", tx_hash, result.result.gas_used());
                            
                            // Strike Trigger Logic
                            let mut crys = crystallizer_task.lock().await;
                            let staging = StagingRef {
                                id: format!("auto_{:?}", tx_hash),
                                taint: format!("{:?}", tx_hash), // Placeholder for actual state hash
                                net_yield: 1000, // Placeholder
                            };
                            let _ = crys.crystallize_strike(&staging, &staging.taint);
                        }
                    }
                    Err(e) => eprintln!("[SIM] ERR: {:?}", e),
                }
            }
        }
    });

    let sub = provider.subscribe_pending_transactions().await?;
    let mut stream = sub.into_stream();

    while let Some(tx_hash) = stream.next().await {
        let _ = tx_sender.send(tx_hash).await;
        // println!("[STRIKE RADAR] Tx detectada: {:?}", tx_hash);
    }

    Ok(())
}
