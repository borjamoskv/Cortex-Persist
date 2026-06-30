---
type: "epistemic-primitive"
domain: "llm-security"
confidence: "C5-REAL"
---

# Primitivas Adversariales en Modelos de Lenguaje (LLMs)

**Postulado**: La seguridad de un LLM no es un estado binario, sino la resistencia termodinámica ante vectores asimétricos que buscan colapsar su función de onda semántica o extraer su grafo de entrenamiento.

## Nodos de Inyección y Corrupción
- **Perturbación de Tokens (Token Flipping)**: Inversión atómica de un token de entrada para forzar un desvío determinista en la predicción del modelo.
- **Ataque de Ejemplo Adversario (FGSM/PGD)**: Inyección de ruido sub-perceptivo calculado mediante gradientes para subvertir el clasificador.
- **Inyección de Datos (Model Poisoning)**: Contaminación ex-ante del conjunto de entrenamiento para instaurar sesgos o comportamientos anómalos.
- **Ataque de Puerta Trasera (Backdoor Trigger)**: Asociar patrones específicos (triggers) a etiquetas falsas. La red se convierte en un autómata que salta de estado ante estímulos condicionados.

## Vectores de Ruptura Estructural
- **Ataque de Integridad**: Desviación forzada del vector de salida para inutilizar el output.
- **Ataque de Disponibilidad**: Denegación de servicio (DDoS) cognitivo mediante sobrecarga del cálculo de atención.
- **Ataque de Inferencia (Data Extraction)**: Reconstrucción forense del ledger de entrenamiento mediante la explotación de la memorización paramétrica de los pesos.

## Manipulación del Contexto y Atención
- **Inyección de Prompts (Prompt Injection)**: Sobreescritura del "system prompt" en tiempo de inferencia para romper los límites de contención epistémica.
- **Modificación de Contexto**: Envenenamiento de la ventana de atención con ruido para desalinear la recuperación causal.
- **Ataque de Capas Profundas**: Mutación de activaciones internas forzando desvíos latentes invisibles en la capa superficial.

```yaml
Claim: "El espacio de atención del LLM es un vector vulnerable a disrupción geométrica; la contención requiere límites criptográficos (C5-REAL), no heurísticos."
Proof: { Base: "docs/epistemology/primitivas_adversariales_llm.md", Range: [0, 10], Confidence: "C5-REAL" }
```
