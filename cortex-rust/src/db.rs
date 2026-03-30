use alloy::providers::Provider;
use alloy::pubsub::PubSubFrontend;
use eyre::Report;
use revm::primitives::{AccountInfo, Address, Bytecode, B256, U256};
use revm::DatabaseRef;
use tokio::runtime::Handle;

/// Un conector sincronizado perezoso (Lazy) hacia el IPC local.
pub struct AlloyDB<P> {
    provider: P,
}

impl<P> AlloyDB<P> {
    pub fn new(provider: P) -> Self {
        Self { provider }
    }
}

// Para integrarse con REVM de forma lazy, necesitamos llamadas síncronas.
// Al ejecutarse en un thread pool (spawn_blocking), podemos usar Handle::block_on.
impl<P: Provider> DatabaseRef for AlloyDB<P> {
    type Error = Report;

    fn basic_ref(&self, address: Address) -> Result<Option<AccountInfo>, Self::Error> {
        let p = &self.provider;
        let handle = Handle::current();
        
        // Obtenemos balance, nonce y código de forma concurrente en un entorno async real, 
        // pero aquí bloqueamos el hilo (es esclavo, no bloquea el nodo).
        let balance = handle.block_on(async { p.get_balance(address).await })?;
        let nonce = handle.block_on(async { p.get_transaction_count(address).await })?;
        let code = handle.block_on(async { p.get_code_at(address).await })?;
        
        let bytecode = Bytecode::new_raw(code);
        
        Ok(Some(AccountInfo {
            balance,
            nonce,
            code_hash: bytecode.hash_slow(),
            code: Some(bytecode),
        }))
    }

    fn code_by_hash_ref(&self, _code_hash: B256) -> Result<Bytecode, Self::Error> {
        // En escenarios reales, se implementa con caché.
        Ok(Bytecode::new())
    }

    fn storage_ref(&self, address: Address, index: U256) -> Result<U256, Self::Error> {
        let p = &self.provider;
        let handle = Handle::current();
        
        // Hacemos el casting del index a B256 porque Alloy espera storage key en B256/U256.
        let storage = handle.block_on(async { p.get_storage_at(address, index).await })?;
        Ok(storage)
    }

    fn block_hash_ref(&self, number: u64) -> Result<B256, Self::Error> {
        let p = &self.provider;
        let handle = Handle::current();
        
        // El segundo parámetro en Alloy 0.7 es BlockTransactionsKind
        let block_opt = handle.block_on(async { p.get_block_by_number(number.into(), false.into()).await })?;
        
        if let Some(block) = block_opt {
            let hash = block.header.hash;
            return Ok(hash);
        }
        
        Ok(B256::ZERO)
    }
}
