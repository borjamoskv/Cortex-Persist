/**
 * ============================================================================
 * LA VACUNA (GNOSIS SAFE DEPLOYER) - PROTOCOLO NÉMESIS
 * ============================================================================
 * Objetivo: Desplegar una Bóveda (Smart Contract Wallet) Inexpugnable (2 de 3).
 * Este script automatiza la generación de las 3 Cuentas Propietarias (Signers)
 * y despliega el contrato Safe en la blockchain elegida (Arbitrum por defecto).
 * ============================================================================
 */

require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');
const Safe = require('@safe-global/protocol-kit').default;
const SafeFactory = require('@safe-global/protocol-kit').SafeFactory;
const { EthersAdapter } = require('@safe-global/protocol-kit');

// === CONFIGURACIÓN DE RED ===
// Por defecto usamos Arbitrum para el despliegue porque el gas es de centavos ($0.05).
// Si quieres Mainnet Ethereum, cambia el RPC.
const RPC_URL = process.env.RPC_URL || "https://arb1.arbitrum.io/rpc"; 
const IDENTITIES_FILE = path.join(__dirname, 'vault_identities.json');

async function main() {
    console.log("🛡️ INICIANDO PROTOCOLO 'LA VACUNA' (GENERADOR DE BÓVEDA SOBERANA) 🛡️\n");

    const provider = new ethers.providers.JsonRpcProvider(RPC_URL);

    let identities;

    // 1. GENERAR O LEER IDENTIDADES
    if (fs.existsSync(IDENTITIES_FILE)) {
        identities = JSON.parse(fs.readFileSync(IDENTITIES_FILE, 'utf-8'));
        console.log("✅ Identidades previas encontradas. Cargando 'Los 3 Pilares'.");
    } else {
        console.log("⏳ Generando 3 Pilares (Wallets Limpias) para el Control Multifirma...");
        identities = {
            signerA: ethers.Wallet.createRandom().privateKey, // Hot Wallet (Móvil)
            signerB: ethers.Wallet.createRandom().privateKey, // Cold 1
            signerC: ethers.Wallet.createRandom().privateKey  // Cold 2
        };
        fs.writeFileSync(IDENTITIES_FILE, JSON.stringify(identities, null, 2));
        console.log("✅ 3 Wallets Creadas y Sombreadas en 'vault_identities.json'.");
        console.log("⚠️ ATENCIÓN: NUNCA SUBAS ESE ARCHIVO A GITHUB. GUARDA ESAS CLAVES EN UN PAPEL DESPUÉS.");
    }

    const walletA = new ethers.Wallet(identities.signerA, provider);
    const walletB = new ethers.Wallet(identities.signerB, provider);
    const walletC = new ethers.Wallet(identities.signerC, provider);

    console.log(`\n--- LOS 3 PILARES ---`);
    console.log(`Pilar A (Deployer/Firma 1) : ${walletA.address}`);
    console.log(`Pilar B (Firma 2)          : ${walletB.address}`);
    console.log(`Pilar C (Firma 3)          : ${walletC.address}`);
    console.log(`-------------------------------------------------\n`);

    // 2. VERIFICAR FONDOS DEL DEPLOYER (Pilar A)
    const balance = await provider.getBalance(walletA.address);
    const balanceEth = ethers.utils.formatEther(balance);

    if (parseFloat(balanceEth) < 0.001) {
        console.log(`❌ ERROR: El Pilar A (Deployer) no tiene fondos (Gas).`);
        console.log(`Tu saldo actual en Arbitrum es: ${balanceEth} ETH`);
        console.log(`\n👉 ACCIÓN REQUERIDA PAR TI:`);
        console.log(`Para poder crear el Smart Contract de tu Bóveda, necesitas enviarle unos céntimos de Ether al Pilar A.`);
        console.log(`1. Ve a Binance/Kraken o a tu wallet actual (si te queda algo vivo).`);
        console.log(`2. Envía 0.005 ETH a la red ARBITRUM a esta dirección: `);
        console.log(`   ${walletA.address}`);
        console.log(`3. Vuelve a ejecutar este script ('node deploy_vault.js').`);
        return;
    }

    console.log(`✅ Fondos detectados en Pilar A: ${balanceEth} ETH. Procediendo al despliegue.`);

    // 3. DESPLIEGUE DEL SAFE (2 de 3)
    const ethAdapter = new EthersAdapter({
        ethers,
        signerOrProvider: walletA
    });

    try {
        console.log("\n⏳ Fabricando los Planos del Smart Contract (SafeFactory)...");
        const safeFactory = await SafeFactory.create({ ethAdapter });

        const safeAccountConfig = {
            owners: [walletA.address, walletB.address, walletC.address],
            threshold: 2 // Aquí es donde se define la regla 2 de 3.
        };

        console.log("🔥 Desplegando en la Blockchain. Por favor, espera... (Puede tardar 10-30 seg)");
        const safeSdk = await safeFactory.deploySafe({ safeAccountConfig });
        const safeAddress = await safeSdk.getAddress();

        console.log("\n============================================================");
        console.log("🎉 ¡LA VACUNA HA SIDO INYECTADA! BÓVEDA CREADA EXITOSAMENTE");
        console.log("============================================================");
        console.log(`🏦 Dirección Pública de tu Gnosis Safe: ${safeAddress}`);
        console.log(`🔗 Ver en el explorador: https://arbiscan.io/address/${safeAddress}`);
        console.log("\n👉 PRÓXIMOS PASOS (ESCARMIENTO FINAL):");
        console.log(`Transfiere el Registrant de borja.moskv.eth y todos tus NFTs valiosos a:`);
        console.log(`-> ${safeAddress} <-`);
        console.log("Nadie, absolutamente nadie podrá robarte los dominios nunca más sin tu Pilar A Y tu Pilar B simultáneamente.");
        
        // Guardamos el safe_address para no olvidarlo
        fs.appendFileSync(IDENTITIES_FILE, `\n\n"SAFE_ADDRESS": "${safeAddress}"`);
        
    } catch (error) {
        console.error("\n❌ Error Crítico durante el Despliegue:");
        console.error(error);
    }
}

main();
