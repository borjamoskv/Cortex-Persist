
📋 PLAN DE BATALLA BRUTAL — CORTEX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Score Inicial: 65/100 (Estimated)
🎯 Misión: EXTERMINAR DEUDA Y MONOLITOS

🌊 Ola 1 (Supervivencia): Fix Build & Security (Passed)
🌊 Ola 2 (Purga): Refactor Monoliths (>300 LOC)
   - [ ] Split `cortex/migrations.py` (412 LOC) -> `cortex/migrations/`
   - [ ] Split `cortex/mejoralo/engine.py` (354 LOC) -> `cortex/mejoralo/core.py`, `cortex/mejoralo/models.py`
   - [ ] Split `cortex/sync/write.py` (337 LOC)
   - [ ] Split `cortex/graph/backends.py` (332 LOC)
🌊 Ola 3 (Ascensión): Optimize Loops & Psi Cleanup
   - No critical Psi debt found.
🌊 Ola 4 (Divinidad): Aesthetics & Polish
   - Ensure clean imports.
   - Run linter.
