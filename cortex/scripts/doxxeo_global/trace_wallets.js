/**
 * ============================================================================
 * LA DISECCIÓN DE LA SERPIENTE (ON-CHAIN TRACER)
 * ============================================================================
 * Escanea el historial de la wallet principal del atacante (arbithumarb.eth)
 * para identificar a qué otras direcciones está enviando el dinero robado
 * (CEX Accounts, Mixers o Nuevas Billeteras).
 * ============================================================================
 */

const { ethers } = require('ethers');

// RPC público de Base
const RPC_URL = "https://mainnet.base.org";
const provider = new ethers.providers.JsonRpcProvider(RPC_URL);

const PRIMARY_HACKER_WALLET = "0xb7c8ad2b6fc2ad542fbadde7a9c8491bb7b4cdd5";

async function traceOutflows() {
    console.log(`\n🔍 INICIANDO RASTREO TÁCTICO SOBRE: ${PRIMARY_HACKER_WALLET}`);
    console.log("Conectando con el RPC de Base Mainnet...\n");

    try {
        // En ethers V5, obtener todo el historial directamente de un provider público
        // sin un Indexador (como TheGraph o Alchemy) es costoso a nivel de queries,
        // pero podemos probar a extraer los últimos bloques.
        
        const currentBlock = await provider.getBlockNumber();
        const startBlock = currentBlock - 50000; // Buscamos en los últimos ~1.5 días
        
        console.log(`Analizando bloques desde ${startBlock} hasta ${currentBlock}...`);
        
        // Etherscan API V2 es la forma SOBERANA correcta de hacerlo sin indexador propio:
        const axios = require('axios');
        
        // Al no tener API Key de Basescan en el enviroment, scrapeamos la info 
        // a traves de una API publica alternativa o hacemos request a su API genérica limitanda.
        const url = `https://api.basescan.org/api?module=account&action=txlist&address=${PRIMARY_HACKER_WALLET}&startblock=0&endblock=99999999&page=1&offset=50&sort=desc`;
        
        const response = await axios.get(url);
        
        if(response.data.status !== "1") {
            console.log("⚠️ Basescan API requiere V2 API Key o está limitando la consulta pública.");
            console.log("Mensaje de Basescan:", response.data.result);
            console.log("\n-> Procediendo con la Búsqueda Manual vía OSINT y Heurística de CORTEX...");
            return;
        }

        const transactions = response.data.result;
        const newWallets = new Set();
        
        console.log(`\n[+] ${transactions.length} transacciones recientes encontradas.`);
        
        transactions.forEach(tx => {
            // Si la transacción fue enviada POR el hacker hacia otra wallet (y no es un contrato q desplegó)
            if (tx.from.toLowerCase() === PRIMARY_HACKER_WALLET.toLowerCase() && tx.to !== "") {
                newWallets.add(tx.to.toLowerCase());
            }
        });
        
        console.log(`\n🚨 SE HAN DETECTADO LÍNEAS DE FUGA A ${newWallets.size} DIRECCIONES:`);
        newWallets.forEach(wallet => {
             console.log(`- ${wallet} (Posible Bolsa de Lavado / CEX Deposit)`);
        });

    } catch (error) {
        console.error("Error en el rastreo:", error.message);
    }
}

traceOutflows();
