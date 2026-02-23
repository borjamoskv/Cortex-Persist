/**
 * ============================================================================
 * EL MARCADOR DE BESTIAS (PUBLIC DOXXING PROTOCOL)
 * ============================================================================
 * Objetivo Automático: Preparar el dossier para el Taint Tracking (Manchado)
 * de las direcciones del cibercriminal Foizur en todos los Block Explorers.
 * (Etherscan, Basescan, Arbiscan, Optimism).
 * 
 * Por política de los Block Explorers, el Etiquetado Oficial de "Phish/Hack"
 * requiere evidencia pública y envío manual a través de su portal de Contacto.
 * Este script empaqueta toda la evidencia legal y genera los links de reporte
 * directo pre-rellenados.
 * ============================================================================
 */

const fs = require('fs');

// Las wallets del Atacante documentadas en el hack
const COMPROMISED_WALLETS = [
    {
        address: "0x7bdc9ce05dc366f07e0cce077f5203ce834cc04c",
        chain: "Base",
        alias: "teamgitcoin.base.eth",
        role: "Contract Deployer / Re-installer"
    },
    {
        address: "0xb7c8ad2b6fc2ad542fbadde7a9c8491bb7b4cdd5",
        chain: "Base",
        alias: "arbithumarb.eth / foizur1999.base.eth",
        role: "Main Wallet / Loot Receiver"
    },
    {
        address: "0xD0De574C37b6de2AE1A614fFEBb939768670CD7F",
        chain: "Base/Arbitrum",
        alias: "KuCoin 4 Looter",
        role: "Funding Anchor"
    }
];

const EVIDENCE_URL = "https://borjamoskv.substack.com/p/take-the-eth-and-run";

console.log("🔥 INICIANDO PROTOCOLO: EL MARCADOR DE BESTIAS 🔥\n");
console.log("Las políticas de Etherscan/Basescan exigen reportes manuales para añadir la etiqueta roja 'Phish/Hack'");
console.log("a una dirección pública. Estoy generando tu munición pre-cargada...\n");

let reportTemplate = `
==============================================
 REPORTE DE DIRECCIÓN COMPROMETIDA 
==============================================
Asunto: Report of Malicious Address (Phishing / EIP-7702 Hack)

Dear Block Explorer Security Team,

I am writing to report the following addresses involved in a highly coordinated EIP-7702 exploitation and phishing campaign targeting Ethereum/Base users.

Primary Attacker Addresses:
`;

COMPROMISED_WALLETS.forEach(w => {
    reportTemplate += `- ${w.address} (${w.role} - ENS: ${w.alias})\n`;
});

reportTemplate += `
Description of the Hack:
The attacker, identified via OSINT as "Foizur" (Telegram: @earning_everytime, Twitter: @arbithumarb), uses social engineering to trick victims into signing off-chain EIP-7702 delegations (chainId=0). Once signed, the attacker deploys a malicious proxy contract replacing the victim's wallet logic, allowing full drain of assets (NFTs and ETH).

Irrefutable Evidence and Autopsy of the Hack:
${EVIDENCE_URL}

We request the immediate tagging of these addresses with the red "Phishing/Hack" warning label to protect other community members from interacting with these contracts.

Thank you.
==============================================
`;

const outputFile = 'doxx_report.txt';
fs.writeFileSync(outputFile, reportTemplate);

console.log(`✅ Dossier generado en: ${outputFile}\n`);
console.log("👉 ACCIÓN SOBERANA PARA EJECUTAR EL DOXXEO:");
console.log("Copia el contenido del archivo generado y envíalo exactamente en estos tres portales:");
console.log("1. BaseScan:  https://basescan.org/contactus?id=5 (Report Scam/Phish)");
console.log("2. EtherScan: https://etherscan.io/contactus?id=5 (Report Scam/Phish)");
console.log("3. ArbiScan:  https://arbiscan.io/contactus?id=5 (Report Scam/Phish)");
console.log("\nEn 24-48 horas, sus billeteras amanecerán con un cartel de advertencia de color sangre.");
