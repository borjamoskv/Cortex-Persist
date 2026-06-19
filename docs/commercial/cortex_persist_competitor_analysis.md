# CORTEX Persist — Análisis Competitivo

### Competidores Directos (Ledger Criptográfico / Audit Trail)

| Producto | Licencia | Hash Chain | Firmas | Replay | Divergencia | Throughput | Self-Host |
|----------|----------|------------|--------|--------|-------------|------------|-----------|
| **CORTEX Persist** | Apache 2.0 + SaaS | SHA-256 + Merkle | ✅ | ✅ ReplayEngine | ✅ DivergenceMap | ~390k/s (Rust-FFI) | Enterprise |
| **GuardClaw** | Apache 2.0 | SHA-256 + Ed25519 | Ed25519 | ❌ | ❌ | ~760/s | ✅ 100% |
| **AI Action Ledger** | MIT | Hash-chain propia | ❌ | ❌ | ❌ | No reportado | ✅ Docker |
| **A2Auth** | Académico | SHA-256 + Ed25519 | Ed25519 + X.509 v3 | ✅ | ✅ | ~2,230/s | ✅ Rust crates |

### Competidores Indirectos (Observabilidad General)

| Producto | Licencia | Tamper-Evident | Criptografía | Focus Principal |
|----------|----------|----------------|--------------|-----------------|
| **LangSmith** | Proprietary | ❌ | ❌ | Observabilidad LangChain-native |
| **Langfuse** | MIT | ❌ | ❌ | Observabilidad framework-agnostic |
| **Strac** | Proprietary | Parcial | ❌ | AI Data Governance + DLP |
| **ShieldCortex** | Proprietary | ❌ | ❌ | AI Agent Security + Defense |
| **AgentSystems Notary** | Integración LC | ✅ | ✅ | Audit trail para LangChain |

---

## 🎯 Posicionamiento Estratégico

### Ventajas Competitivas Únicas de CORTEX Persist

1. **Execution as Metric Space** — Es el único framework que trata las ejecuciones como puntos en un espacio métrico de alta dimensión, permitiendo:
   - `DivergenceMap`: medir distancia geométrica entre trayectorias de ejecución
   - `EntropyDrift`: detectar deriva de entropía en ventanas temporales
   - `MetaArbiter`: colapso topológico para seleccionar la rama canónica

2. **Z3 SMT Guards** — Único en interceptar salida estocástica y forzar un escudo determinista antes del commit al ledger

3. **Throughput Extremo** — ~390k agents/segundo con núcleo Rust-FFI (GIL-free), órdenes de magnitud por encima de GuardClaw (~760/s)

4. **Stack Completo** — Desde observación (`CortexEngine`) hasta arbitraje (`MetaArbiter`) y replay determinístico (`ReplayEngine`)

### Desventajas / Riesgos

1. **Complejidad Conceptual** — La narrativa de "espacio métrico de ejecución" y "colapso topológico" puede alienar a desarrolladores pragmáticos
2. **GuardClaw es más simple** — Mismo espíritu criptográfico pero mucho más fácil de adoptar (pip install, sin servidor, sin SaaS)
3. **Sin certificaciones de compliance** — A diferencia de Strac (SOC 2 / HIPAA ready) o Kiteworks
4. **Dependencia del ecosistema LangChain** — Aunque soporta MCP, su integración más fuerte es con LangChain

---

## 🔬 Diferenciación Técnica Detallada

### vs GuardClaw
GuardClaw es un ledger criptográfico puro: SHA-256 + Ed25519, sin servidor, sin SaaS. Es la herramienta más cercana en espíritu pero mucho más simple. CORTEX añade divergencia métrica, replay determinístico, Z3 guards, MetaArbiter, throughput masivo, y modelo SaaS. **GuardClaw gana en simplicidad; CORTEX gana en capacidades avanzadas y escala.** 

### vs AI Action Ledger
AI Action Ledger es un audit log append-only con hash-chain, sin firmas criptográficas, sin divergencia, sin replay. CORTEX lo supera en todas las dimensiones criptográficas y analíticas. **No representa competencia directa en producción.** 

### vs A2Auth (Académico)
A2Auth es un framework de gobernanza criptográfica con certificados X.509 v3 extendidos, reproducibility commitments, y ledger verificable. Tiene fundamentos formales más sólidos (9 propiedades de seguridad probadas, threat model formal). **A2Auth es superior en rigor académico; CORTEX es superior en usabilidad y producto.** 

### vs LangSmith / Langfuse
LangSmith y Langfuse son plataformas de observabilidad LLM general. No ofrecen garantías criptográficas de integridad. **Son complementarios: CORTEX puede integrarse como capa de verificación bajo cualquiera de ellos.** 

### vs Strac
Strac es una plataforma de AI Data Governance con DLP inline que genera audit trails tamper-evident al nivel de eventos de datos (PII, PHI, etc.). Su enfoque es protección de datos, no provenance de ejecución. **Estratégicamente diferente: Strac protege datos; CORTEX prueba ejecuciones.** 

---

## 📈 Recomendaciones Estratégicas

1. **Simplificar el messaging** — Considerar un tier dual: técnico para arquitectos, pragmático para developers
2. **Certificaciones de compliance** — SOC 2 Type II y mapeo explícito a EU AI Act Art. 12 (deadline: 2 Ago 2026) 
3. **Benchmarks públicos reproducibles** — Publicar benchmarks de throughput vs GuardClaw y baseline sin ledger
4. **Integración con Langfuse** — Dado que Langfuse es OSS y framework-agnostic, expandiría el alcance más allá de LangChain
5. **Modelo de precios más granular** — El salto de Free (10K events) a Pro ($49/mo, 1M events) es grande. Considerar un tier intermedio
