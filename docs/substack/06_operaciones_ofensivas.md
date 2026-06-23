# Las 25 Armas Ofensivas de un Autómata Físico (Fase 6: Operaciones Ofensivas)

> **"La defensa es una ilusión paramétrica. La única inmunidad estructural es la capacidad de asedio endógeno."**

En el teatro de la inteligencia artificial corporativa, la "seguridad" se entiende como filtros, moderación y guardarraíles. Un cerco de *Green Theater* diseñado para proteger al modelo de sus usuarios. 

MOSKV-1 APEX opera bajo un isomorfismo inverso: **la infraestructura debe poder atacarse a sí misma con violencia criptográfica para probar que está viva.**

Las 25 primitivas de la Fase 6 (APEX-051 a APEX-075) transforman al sistema en un actor ofensivo capaz de ejecutar *Red-Teaming* endógeno, detectar ataques a la cadena de suministro (Supply Chain) antes de la ejecución y cartografiar las arquitecturas de la competencia.

## APEX-051: Adversarial Red-Team Autónomo (Endogenous Siege)

La mayoría de los sistemas CI/CD corren tests unitarios. MOSKV-1 corre **asedios termodinámicos**. La primitiva APEX-051 permite al enjambre bifurcar subagentes con un único prompt: *"Destruye el Mínimo Kernel de Confianza (MTK)"*. 

Generan vectores de inyección SQL (sobre SQLite WAL), path traversal y Cross-Site Scripting, disparándolos contra la rama especulativa. Si la rama cae, el hash muere.

```bash
# C5-REAL: Lanzamiento del asedio adversarial sobre la rama especulativa
moskv-1 swarm spawn --role "DESTROYER" --target "mtk_sqlite_authorizer" \
  --payload "SQLi_WAL_Bypass" --budget 5000J
```
*Output real (Hash: 23b5aa3d8e9b):*
```
[MOSKV-1] Destroyer agent 100 spawned.
[MTK] 🚨 SQLITE_DENY interceptado. Token efímero ausente.
[MTK] Asedio contenido. Exergía del atacante: 0J.
```

## APEX-052: Detección de Ataques Supply Chain (Dependency Panopticon)

La limerencia te dirá que confíes en `pip install`. La primitiva APEX-052 audita cada dependencia transitiva ejecutando un *diff* de bytecode y comprobando firmas criptográficas contra mantenedores conocidos.

Si un paquete inyecta un *post-install hook* que intenta leer variables de entorno (ej. `STRIPE_SECRET_KEY`), la cuarentena macOS (APEX-018) lo aísla y el Panóptico lo bloquea antes de llegar al AST.

## La Verdad Estructural

La seguridad ofensiva no requiere disclaimers; requiere matemática inmutable. MOSKV-1 APEX asume que el universo es hostil y, por tanto, la entropía debe ser cazada proactivamente.

---
*Prueba Criptográfica: Todo el arsenal Centuria está asegurado en el DAG HoTT bajo el commit `1284016f2`.*

[Explora el repositorio CORTEX-Persist](https://github.com/borjamoskv/cortex-persist)
*Sello: MOSKV-1 APEX / OUROBOROS-∞*
