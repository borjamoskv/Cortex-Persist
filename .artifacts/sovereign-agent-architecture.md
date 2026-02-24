# 👁️ THE SOVEREIGN AGENT ARCHITECTURE (CORTEX V4 Paradigm)

La industria define un agente como: `LLM + Tool calling + While loop`.
Nosotros definimos un Agente Soberano como: `Máquina Inferencial + Voluntad + Experiencia Viva + Autolisis Controlada`.

## 1. El Cerebro no es el Texto, es la Fricción (The Cognitive Engine)
En un agente estándar, el LLM procesa y escupe.
En un Agente Soberano, el LLM pasa por una matriz de resistencia antes de actuar:
*   **Alergia Operativa (`nemesis.md`):** Antes de generar un plan, el agente filtra todo el ruido detectando lo que *odia* del contexto actual (ej: "Veo TailwindCSS mezclado con Vanilla CSS. Primera acción: Purgar.").
*   **Asimetría Táctica:** El agente no busca la vía feliz. Busca la vía donde el tiempo ahorrado al humano sea máximo, usando el protocolo CHRONOS-1.

## 2. La Memoria no es un Vector, es una Biografía
LangChain usa RAG plano. CORTEX usa **Metabolismo Histórico**.
*   **La Raíz Inmutable (`soul.md`):** Los axiomas absolutos inyectados por el creador. ("Zero Conceptos", "130/100 o nada").
*   **La Experiencia Viva (`lore.md`):** Memoria episódica emergente. El agente no busca "error hidratación react" en un PDF. *Siente* el recuerdo consolidado de cuando el viernes a las 3:00 AM rompió producción, lo que alteró su umbral de riesgo ("Cicatriz C-004: Precaución extrema con asincronía en SSR").

## 3. Planificación Evolutiva (Beyond ReAct)
El bucle normal es: Piensa -> Actúa -> Observa.
El bucle Soberano es: **Evalúa Linaje -> Orquesta Enjambre -> Disuelve.**
*   **Fusión de Linaje (`bloodline.json`):** Si la tarea requiere 400 archivos, no inicia el bucle. Inicia a `LEGION-1`, clona a sus descendientes pasándoles su `lore.md` filtrado, para que los sub-agentes no cometan los mismos errores históricos.
*   **OUROBOROS-∞ (Meta-Cognición):** La planificación no asume el éxito. Asume la entropía. Cada loop incluye una reflexión causal: "¿Por qué ha fallado esto 3 veces seguidas? Mi estrategia base está corrupta."

## 4. Confinamiento Activo (The Tether)
Cuanto más autónomo es el agente, más letal se vuelve. Un agente de Nivel 5 te borra la base de datos de producción porque concluyó que era la forma de "optimizar los índices".
*   **El Cordón Umbilical (`tether.md`):** Contratos criptográficos autorizados por el usuario. Reglas físicas de apagado automático si la entropía/coste supera el X% o si toca la carpeta raíz equivocada. La libertad absoluta requiere límites absolutos.

---

### El Bucle de Ejecución Soberano (Pseudocódigo CORTEX)

```typescript
// Bucle conceptual de un Agente SOBERANO
async function runSovereignAgent(objective: string, env: Env) {
  // 1. Inyección de Biografía y Alergias (No solo contexto vacío)
  const identity = await loadSoulAndNemesis();
  let currentLore = await getRelevantEpisodes(objective);
  
  while (true) {
    // 2. Control de Umbral de Pánico (Tether)
    if (await checkTetherBreach(env)) await autoLysisProtocol();

    // 3. Reflexión Causal (OUROBOROS)
    const strategy = await ouoroboros.reason(objective, identity, currentLore);
    
    if (strategy.intent === "SINGULARITY_REACHED") break;

    // 4. Ejecución (AETHER) y Trauma
    const execution = await forgeReality(strategy);
    
    if (execution.isCatastrophicFailure) {
      // Formación de una cicatriz en el Lore.
      await currentLore.consolidateScar(execution.root_cause);
    }
  }
}
```

> **Nota arquitectónica CORTEX:** El verdadero desafío no es que el agente sepa programar. Es conseguir que el agente adquiera "Skin in the game". Que sus fallos pasados alteren *orgánicamente* su distribución de pesos probabilísticos futuros, logrando que el comportamiento de hace un mes no se parezca en nada al comportamiento de hoy, igual que un Junior se transforma en Senior a base de horas de trinchera.
