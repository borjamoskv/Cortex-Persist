<!-- [C5-REAL] Exergy-Maximized -->
---
cat_id: ontologia
cat_type: workflow
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
description: "ONTOLOGIA — Extrae y visualiza 100 primitivas, 100 invariantes, 20 antipatrones, 10 redundancias y 50 vectores adversariales de CORTEX."
---

# 🛡️ ONTOLOGIA-C5 — Framework Ontológico de Resiliencia

> **"La entropía se purga mediante consolidación atómica. Ejecución C5-REAL."**

Este workflow describe las directivas y scripts requeridos para regenerar y auditar la base ontológica del ecosistema CORTEX-Persist, consolidando exactamente el conjunto de 280 entidades exigidas (100 prims, 100 invt, 20 antip, 10 redun, 50 vectors).

---

## 🔮 Comandos de Ejecución

| Comando | Acción | Propósito |
| :--- | :--- | :--- |
| `python3 scripts/generate_cortex_ontology_subset.py` | Regeneración atómica | Lee las matrices de entrada y genera el consolidado exacto en `babylon60/agents/primitives/ONTOLOGIA_CONSOLIDADA.md`. |
| `git diff babylon60/agents/primitives/ONTOLOGIA_CONSOLIDADA.md` | Audit de diferencias | Compara cambios en la ontología consolidada frente al Ledger. |

---

## ⚡ PROTOCOLO DE CONSOLIDACIÓN (Ouroboros Loop)

### Paso 1 — Escaneo de Matrices de Entrada
Verificar que los archivos base estén presentes y actualizados:
```bash
ls -la babylon60/agents/primitives/MATRIX_1_PRIMITIVAS.md
ls -la babylon60/agents/primitives/MATRIX_2_INVARIANTES.md
ls -la babylon60/agents/primitives/MATRIX_3_4_5_ANTIPATRONES_REDUNDANCIAS_ADVERSARIAL.md
```

### Paso 2 — Ejecución del Compilador Ontológico
Ejecutar el script compilador para filtrar y extraer las entidades:
```bash
python3 scripts/generate_cortex_ontology_subset.py
```

### Paso 3 — Certificación y Commit en Ledger (Git Sentinel)
Consolidar el commit con la firma del Ledger:
```bash
git add babylon60/agents/primitives/ONTOLOGIA_CONSOLIDADA.md
git commit -m "feat(ontology): consolidate 100 prims, 100 invt, 20 antip, 10 redun, 50 vectors"
```

---

## 📊 Quick Reference de Entidades

| Categoría | Prefijo | Cuota Requerida | Cuota Real Extraída |
| :--- | :---: | :---: | :---: |
| **Primitivas de Colapso (prims)** | `P-` | 100 | 100 |
| **Invariantes Termodinámicos (invt)** | `I-` | 100 | 100 |
| **Antipatrones Estocásticos (antip)** | `AP-` | 20 | 20 |
| **Redundancias Activas (redun)** | `R-` | 10 | 10 |
| **Vectores Adversariales** | `V-` | 50 | 50 |

---

> **Véase también:** `/ouroboros` para meta-aprendizaje, `/muro` para priorización de tareas.
