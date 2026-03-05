# 🏴‍☠️ PROTOCOLO SOBERANO: OPENSEA AIRDROP (TGE)

> **[moneytv-1 TRANSCENDENCE ACTIVE]**
> *Status: ALERTA ROJA (High Conviction)*
> *Risk Level: Medio (Phishing / Gas War)*

## FASE 0: DEFENSA (Zero-Trust Model)
- [ ] **NO GOOGLEAR**: Los primeros resultados de "OpenSea Airdrop" serán ad/phishing drainers.
- [ ] **FUENTE ÚNICA**: Entrar única y exclusivamente desde el Twitter oficial: `https://twitter.com/opensea` o la web que ya tienes bookmarked `https://opensea.io`.
- [ ] **AISLAMIENTO**: Usar un navegador/perfil estricto sin extensiones extrañas para el claim.
- [ ] **RABBIT HOLE**: Revisa permisos de la wallet antes de firmar CUALQUIER transacción (si no pone "Claim" y pone "SetApprovalForAll", abortar inmediatamente).

## FASE 1: PREPARACIÓN LOGÍSTICA
- [ ] **FONDOS PARA GAS**: Asegurar mínimo de `$50-$100` en ETH en cada wallet elegible para absorber los picos de gas de la congestión.
- [ ] **SYBIL RESISTANCE**: Si tienes múltiples wallets elegibles, transfiere fondos de gas desde un CEX (Binance, Kraken), NUNCA entre ellas. De igual modo, no las juntes a la hora de vender.
- [ ] **TRACKER DE GAS**: En `~/cortex/airdrops/opensea/gas_sniper.py` he dejado forjado un monitor asíncrono para avisarte acústicamente cuando el Gwei baje de un target (por defecto 40.0 Gwei).

## FASE 2: EJECUCIÓN (El Snipe)
1. Si la red colapsa (>200 Gwei) y tu alocación no supera las 4 cifras, **NO CLAIMEES EN EL MINUTO 1**. El gas te devorará el ROI. 
2. Invoca el sniper en background y espera a la ventana óptima:
   ```bash
   python3 ~/cortex/airdrops/opensea/gas_sniper.py 40.0
   ```
3. Alternativamente, si el claim es via L2 (Base / Arbitrum / Polygon), el estrés de gas será marginal pero habrá congestión de RPCs. Si falla la transacción, cambiar de RPC en Metamask/Rabby (usa Alchemy o Infura).

## FASE 3: POST-CLAIM & PROFIT TAKING (Regla de moneytv-1)
- [ ] Calcula P&L neto (Token Value - Gas Cost).
- [ ] **DECISIÓN DIRECCIONAL**: 
  - ¿Hay presión de venta masiva de early farmers? **Vender el 50-70% inmediatamente** para recuperar EV (Expected Value) y mitigar riesgo de dump orgánico post-TGE.
  - Mantener moon-bag (20-30%) en frío por si hay un squeeze secundario propulsado por market makers.
- [ ] **CORTEX COMMIT**: Logguear la rentabilidad total en ~/.cortex para alimentar CHRONOS-1 y ajustar proyecciones anuales.

## REGLA DE SUPERVIVENCIA
> "Si dudas, no hagas el trade." - *moneytv-1 RiskManager*
