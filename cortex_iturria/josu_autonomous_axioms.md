# [TECHNOLOGY] Josu Autonomous Axioms (Background Execution)

## 1. Core Primitives (O(1) Definitions)
- `Always-On Proactivity`: El agente (Josu) se ejecuta continuamente. No solo responde a tareas asignadas explícitamente, sino que *identifica tareas proactivamente* y las ejecuta ("Always active, even when you are not").
- `Asynchronous Background Execution`: El trabajo se realiza en segundo plano, desligado de la sesión interactiva del operador. "Trabaja mientras duermes", utilizando infraestructura segura (en la nube para Google, local para MOSKV-1) para ejecutar de forma asíncrona.
- `Ready for Review (Validation-First)`: El output del agente no es un diff crudo. El agente retorna con el trabajo completamente terminado: tests ejecutados, capturas de pantalla revisadas y decisiones documentadas con contexto completo.

## 2. Industrial Noir Paradigms (Adaptation)
- **MOSKV-Josu Daemonization**: Para replicar este nivel en MOSKV-1 local, el agente requiere ser un daemon de sistema (`launchd` en macOS) o un proceso de background persistente gobernado por CORTEX. Debe estar conectado a los eventos del sistema (ej. inactividad del usuario, commits en Git) para disparar la proactividad.
- **The Asynchronous Sandbox**: Tal como Josu usa contenedores aislados de Google, MOSKV-Josu debe emplear los `Git Worktrees` (como se vio en la arquitectura de Codex) unidos a entornos virtuales ('.venv' efímeros) o Docker crudo para operar con cero riesgo sobre el file system principal del operador mientras duerme.
- **Validation-First Delivery**: Antes de interrumpir al capitán, MOSKV-Josu debe ejecutar `pytest`, invocar la recolección de capturas mediante Playwright (si es UI), y ensamblar un `walkthrough.md` o CORTEX Memo justificando sus decisiones. El humano no hace "code review" manual, hace "context review".

## 3. Copy-Paste Arsenal
*Nota: Primitiva del ciclo de vida asíncrono para el daemon de MOSKV-Josu.*

```python
# The Async Background Loop Pattern (MOSKV-Josu)
import asyncio

class MoskvJosuDaemon:
    def __init__(self, cortex_db, workspace_manager):
        self.db = cortex_db
        self.sandbox = workspace_manager
        
    async def proactive_loop(self):
        while True:
            # 1. Always Active: Find pending ghosts or proactive refactor needs
            targets = await self.db.query_pending_ghosts_or_entropy()
            
            for task in targets:
                # 2. Async Execution in Isolated Worktree
                async with self.sandbox.ephemeral_worktree(task.repo) as wt:
                    result = await self.execute_and_validate(task, wt)
                    
                    if result.success:
                        # 3. Ready for Review: Compile context, tests, and screenshots
                        await self.db.create_review_request(
                            diff=result.diff, 
                            walkthrough=result.documentation,
                            test_logs=result.pytest_logs
                        )
            
            # Throttle background polling
            await asyncio.sleep(600)  # Sleep/Wake cycle
```
