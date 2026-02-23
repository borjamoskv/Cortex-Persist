# VECTOR 4: RESCATE SOBERANO (MEV / FLASHBOTS) 🏴‍☠️

El hacker tiene un **Sweeper Bot** vigilando tu billetera 24/7. 
Si envías el ETH necesario para poder firmar el airdrop de OpenSea, él te lo robará en milisegundos y tú te quedarás sin ETH y sin tokens.

Este entorno **Node.js** está preparado para eludir ese ataque usando **Miner Extractable Value (MEV)**. 
En lugar de mandar tus peticiones a la piscina pública de Ethereum (*mempool*), se la entregamos en secreto y en mano a un validador a través de Flashbots. 

## El "Bundle" Atómico

El script `index.js` agrupa tres cosas en una bala que dura solo 1 bloque:
1. Mete fondos de gas (provenientes de una nueva wallet oculta tuya).
2. Firma el *Claim* del airdrop (con tu wallet hackeada, que ahora tiene gas secreto).
3. Transfiere los tokens $SEA instantáneamente a tu nueva Gnosis Safe.

**Velocidad:** Las tres ocurren en el mismo instante matemático para la red. El hacker queda cegado.

---

## 🔥 INSTRUCCIONES PARA EL "DÍA D" (Q1 2026)

**Paso 1: Prepara tus claves (Local)**
1. Duplica `.env.template` y renómbralo a `.env`.
2. Consigue una URL de un RPC privado (Recomendado: Alchemy o Infura gratuito). No uses Cloudflare o LlamaNodes. Ponla en `RPC_URL`.
3. Crea y fondea una Wallet Limpia con unos 0.05-0.10 ETH. Pon su calve privada en `FUNDER_PRIVATE_KEY`.
4. Busca y pon la clave de tu wallet hackeada en `COMPROMISED_PRIVATE_KEY`.

**Paso 2: Rellena los Contratos de OpenSea (Día Anuncio)**
Abre `index.js` y modifica:
```javascript
const OPENSEA_AIRDROP_ADDRESS = "0x_DIRECCION_QUE_PUBLIQUE_OPENSEA";
const SEA_TOKEN_ADDRESS = "0x_CONTRATO_DEL_TOKEN_SEA";
const RECOVERY_ADDRESS = "0x_DIRECCION_DE_TU_GNOSIS_SAFE";
```

**Paso 3: Fuego**
Ponte en el directorio `/scripts/mev_rescue` y ejecuta:
```bash
node index.js
```

## 🧠 Notas Soberanas
* Si el console dice "✅ Simulación exitosa", tu bundle es perfecto. 
* Si dice "❌ Nonce demasiado alto" o algo similar, cancela rápido y revisa. 
* Este script NUNCA gasta a lo ciego. Si el bloque no puede minarse de manera atómica con los 3 pasos exactos, el minero descarta el paquete y **NO PAGAS NADA DE GAS**. Es un sistema "Todo o Nada". No hay riesgo de perder fútilmente los valiosos fondos del Funder.
