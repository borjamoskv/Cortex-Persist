# CORTEX Deep Research: Lido Simple DVT (SDVT)
**Operación LEVIATHAN — Fase 4: UltraThink Synthesis**

## 1. Topología de la Arquitectura SDVT
El módulo "Simple DVT" de Lido no utiliza un smart contract radicalmente nuevo para el registro. En su lugar, inicializa una instancia independiente del contrato `NodeOperatorsRegistry.sol` de Lido V2, conectada al `StakingRouter`.

La revolución del módulo ocurre off-chain y en la capa de recompensas:
1. **Lógica de Validación:** Los validadores están fragmentados mediante DKG (Distributed Key Generation) usando infraestructura **Obol Network** (Charon) o **SSV Network**.
2. **Recepción de Recompensas (Execution Layer):** Las fee recipients no apuntan a los operadores individuales, sino a contratos **0xSplits** pre-configurados. `0xSplits` enruta de forma inmutable (o controlada por multisig) los balances de MEV/Priority fees entre los nodos participantes del clúster y la DAO de Lido.

## 2. Superficie de Ataque Teórica (Vectores P0/P1)

### Vector A: Secuestro del Split Contract (MEV Hijacking)
- **Concepto**: El `feeRecipient` de los bloques propuestos debe apuntar al smart contract de *0xSplits* del clúster.
- **Explotación**: Si el contrato *split* es mutable (tiene un *controller* vivo) y las llaves de dicho *controller* son vulneradas, un atacante podría redirigir el 100% de los MEV rewards generados por el clúster (7 nodos) hacia su billetera, saltándose el diezmo de Lido.
- **Mitigación Observada**: Lido exige que los Splitting Contracts sean **inmutables** tras su despliegue, bloqueando el controlador.

### Vector B: Colusión de DKG y Secuestro de Firmas de Salida
- **Concepto**: Un clúster (ej. 5-of-7) requiere coordinación para generar las firmas BLS.
- **Explotación**: Si 5 operadores maliciosos forman un cartel o si un nodo genera firmas EIP-7002 (Voluntary Exits) de forma encubierta, pueden forzar la expulsión masiva del clúster. 
- **Mitigación Observada**: La capa de consenso exige que los exit messages provengan de las credenciales de retiro de Lido, no de las BLS keys fragmentadas. Obol/Charon limita la firma de exits sin quorum.

### Vector C: Asimetría de Penalizaciones (Slashing Socialization)
- **Concepto**: Un único operador incompetente o malicioso no puede causar un *slash* si el umbral no se alcanza (ej. 4 nodos buenos sobre 7).
- **Explotación**: Sin embargo, si 5 nodos acuerdan comportarse de forma bizantina (firmar certificados dobles), toda la porción de ETH penalizada será absorbida por la liquidez global de Lido (stETH buffer). Los 2 nodos honestos sufrirán sin haber participado.
- **Mitigación Observada**: Lido mitiga esto requiriendo un bond/fianza inicial y aplicando un límite de capacidad (Stake Router Module Cap) para contener el radio de explosión a un pequeño porcentaje del TVL total.

## 3. Conclusión de UltraThink
El módulo SDVT está diseñado como un **sandbox termodinámico**. Carece de riesgos sistémicos de *smart contract* (dado el reuso de `NodeOperatorsRegistry` y `SSV/0xSplits` ya auditados). Las verdaderas vulnerabilidades radican en la ingeniería social del DKG y en ataques de cartel inter-operador off-chain.

El veredicto estructural de CORTEX sobre Lido Simple DVT es: **Altamente Resiliente**. El aislamiento del riesgo en el `StakingRouter` descarta cualquier vector de contención cruzada.
