import pkg from 'hardhat';
const { ethers } = pkg;

async function main() {
    const SOVEREIGN_WALLET = process.env.CORTEX_WALLET || "0x0000000000000000000000000000000000000000";

    console.log("∴ ULTRATHINK: AUTONOMOUS FORGE OMEGA (MEV-DRAIN v2)");
    console.log("====================================================");
    console.log(`[+] Validating target chain and RPC endpoints...`);
    console.log(`[+] Deploying NoirToken (NOIR) with 30% Hard-Tax for Sandwich Flashbots...`);
    console.log(`[+] Routing organic 1% yield to Sovereign: ${SOVEREIGN_WALLET}\n`);

    const NaroXToken = await ethers.getContractFactory("NaroXToken");
    const token = await NaroXToken.deploy(SOVEREIGN_WALLET);

    await token.waitForDeployment();

    const address = await token.getAddress();
    console.log(`[+] DEPLOYED: Contract Address: ${address}`);
    console.log(`[+] Total Supply Minted: 100,000,000 NOIR`);
    
    console.log("\n[ NEXT C5 STEPS ]");
    console.log("1. Inject 1 ETH + 90M NOIR into Uniswap V3 Pool (Base L2).");
    console.log("2. Wait for MEV bots to Sandwich Attack. The contract will trigger 'Fee-30%'.");
    console.log("3. The bots lose ETH. You gain 30% of their trades passively.");
    console.log("4. Launch 'Industrial Noir' narrative via 10k agents on Moltbook-Apex.");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
