# 🧠 CORTEX Domain: MOSKV-SWARM

## 🔍 NOTAS DE INVESTIGACIÓN (CRÍTICO)
> NotebookLM: He detectado las siguientes lagunas en CORTEX para este proyecto.
- Hay **72** hechos sin verificar que requieren validación lógica.
- Las siguientes entidades carecen de conexiones relacionales: SecurityCompliance.

## Base de Conocimiento
### Error
- **ERROR: API key Kimi/Moonshot invalid or expired | CAUSA: Moonshot API keys have expiration — stored key was not rotated | FIX: Implement key rotation check on startup, validate key before first API call** (Confid: verified)
- **ERROR: Strategy returned None/invalid in KimiBrain | CAUSA: LLM response parsing assumes structured output but Kimi sometimes returns free-form text | FIX: Add fallback parser + retry with structured prompt if first parse fails** (Confid: verified)
- **ERROR: El Python del sistema macOS (Apple framework build) no soporta sqlite load_extension. Usar siempre Homebrew Python en venvs** (Confid: verified)
- **ERROR: API keys de Kimi/Moonshot caducan sin aviso. SwarmBrain migrado a Grok 4.1 via OpenRouter como cerebro principal** (Confid: verified)
- **ERROR:  | CAUSA:  | FIX: ** (Confid: verified)
### Decision
- **Reemplazar Kimi K2.5 por Llama o Grok — API key Kimi expirada, no renovar. Evaluar Llama (local) vs Grok (API) como brain del swarm.** (Confid: stated)
- **Solución de prueba: deploy exitoso** (Confid: verified)
- **Misión CTR-0001-655: Crea una ruta de API para registrar usuarios nuevos en el sistema

🧠 [CORTEX] CONTEXTO HISTÓRICO:
-  → Resolución: {'NeuralMixer': {'error': 'Agent NeuralMixer has no execute/run method'}, 'CREATIVE.AUDIO.synthesizer': {'agent': 'CRE.AUDI.synthe.e8de639f', 'status': 'success', 'result': {'agent_id': 'CRE.AUDI.synthe.e8de639f', 'signature': 'e8de639f3583f294', 'division': 'CREATIVE', 'squad': 'AUDIO', 'specializa** (Confid: verified)
- **Preferimos FastAPI sobre Flask por la validación de tipos nativa, async support y documentación OpenAPI automática** (Confid: verified)
- **Nunca exponer puertos de bases de datos al exterior. Usar siempre túneles SSH, redes internas Docker o proxies autenticados** (Confid: verified)
- **Para despliegues en producción siempre usar imágenes Docker distroless o slim. Nunca ejecutar procesos como root** (Confid: verified)
- **Todos los secretos y API keys van en variables de entorno (.env), nunca hardcodeados en el código fuente** (Confid: verified)
- **El código Python debe seguir PEP8. Docstrings en formato Google. Type hints obligatorios en funciones públicas** (Confid: verified)
- **Logging con el módulo estándar logging (lazy % formatting, no f-strings). Niveles: DEBUG para desarrollo, INFO para operaciones, WARNING+ para problemas** (Confid: verified)
- **Frontend Naroa: Vanilla JS + CSS puro, sin frameworks. Aesthetic Industrial Noir con glassmorphism y micro-animaciones** (Confid: verified)
- **Base de datos por defecto: SQLite para proyectos locales y prototipos. PostgreSQL para producción con más de 100K registros** (Confid: verified)
- **Estética Industrial Noir — paleta BLUE YLN-LM para todo el ecosistema Moskv. Colores: azules oscuros, acentos neón, tipografía monoespaciada** (Confid: verified)
- **Naroa brand: hiperrealismo POP, colores vibrantes, tipografía humanista. No usar estética industrial en proyectos de Naroa** (Confid: verified)
- **Misión CTR-0001-942: Diseña la arquitectura de microservicios para el sistema de streaming de video

🧠 [CORTEX] CONTEXTO  → Resolución: {'AlcoveIntelAgent': {'error': 'Agent AlcoveIntelAgent has no execute/run method'}, 'AestheticAgent': {'error': 'Agent AestheticAgent has no execute/run method'}, 'PerformanceHawk': {'error': 'Agent PerformanceHawk has no execute/run method'}, 'SEOOptimizer': {'error': 'Agent SEOOptimizer has no exe** (Confid: verified)
- **Misión CTR-0001-1138 completada. Consenso: 83%. Mejor agente: APIDesigner** (Confid: verified)
- **Misión CTR-0001-1138: Diseña la arquitectura de microservicios para el sistema de streaming de video

🧠 [CORTEX] CONTEXTO  → Resolución: {'SecurityCompliance': {'agent': 'SecurityCompliance', 'status': 'success', 'result': {'status': 'completed', 'analysis': 'No code provided for compliance check.'}, 'elapsed': 0.0, 'mission': 1}, 'APIDesigner': {'agent': 'APIDesigner', 'status': 'success', 'result': {'status': 'completed', 'design':** (Confid: verified)
- **STEEL_FORGE agents refactored: PerformanceHawk hereda de BaseAgent con execute(), DockerArchitect/APIDesigner/SecurityCompliance estandarizados con lectura segura de CORTEX context, print reemplazado por logging, scoring extraido a utils** (Confid: stated)
### Knowledge
- **Comando global cortex instalado vía symlink en ~/.local/bin** (Confid: stated)
- **Integration test: CORTEX bridge funcional con búsqueda semántica** (Confid: stated)
- **En el backend usamos validación estricta con Pydantic para todos los endpoints** (Confid: verified)
- **Misión CTR-0001-655: formación FORJA_SONORA con 4 agentes** (Confid: stated)
- **Misión CTR-0001-655 disputada. Solo 25% aprobación.** (Confid: hypothesis)
- **En el backend usamos validación estricta con Pydantic para todos los endpoints y modelos de datos** (Confid: verified)
- **Arquitectura de microservicios: cada servicio es independiente con su propia DB, comunicación via REST o eventos asíncronos** (Confid: verified)
- **Autenticación: usar JWT con tokens de corta duración (15min access, 7d refresh). Hashear passwords con bcrypt, nunca MD5 o SHA-1** (Confid: verified)
- **CI/CD: GitHub Actions para tests y deploy. Vercel para frontend estático. Docker Compose para servicios locales** (Confid: stated)
- **Misión CTR-0001-942: formación SPARK_WEB con 6 agentes** (Confid: stated)
- **Misión CTR-0001-942 disputada. Solo 17% aprobación.** (Confid: hypothesis)
- **Misión CTR-0001-1138: formación STEEL_FORGE con 6 agentes** (Confid: stated)
- **Mission M-0001: {"status": "success", "analysis": "Code audit for: Analiza la arquitectura del sistema moskv", "issues": [], "complexity_score": 0.0, "quality_grade": "A", "agent": "CodeAuditor"}** (Confid: stated)
- **The secret code for the audit is: OMEGA-99** (Confid: stated)
- **The secret code for the audit is: OMEGA-99** (Confid: stated)
- **MISSION SUCCESS: 'Perform security audit using the secret code.'
Formation: Iron Dome
Agents: SecurityCompliance, SecurityCompliance, SecurityCompliance
Context: - The secret code for the audit is: OMEGA-99
- The secret code for the audit is: OMEGA-99
- Autenticación: usar JWT con tokens de corta duración (15min access, 7d refresh). Hashear passwords con bcryp...** (Confid: stated)
- **The secret code for the audit is: OMEGA-99** (Confid: stated)
- **MISSION SUCCESS: 'Perform security audit using the secret code.'
Formation: Iron Dome
Agents: SecurityCompliance, SecurityCompliance, SecurityCompliance
Context: - MISSION SUCCESS: 'Perform security audit using the secret code.'
Formation: Iron Dome
Agents: SecurityCompliance, SecurityCompliance, SecurityCompliance
Context: - The secret code for the audit is: ...** (Confid: stated)
- **The secret code for the audit is: OMEGA-99** (Confid: stated)
- **MISSION SUCCESS: 'Perform security audit using the secret code.'
Formation: Iron Dome
Agents: SecurityCompliance, SecurityCompliance, SecurityCompliance
Context: - MISSION SUCCESS: 'Perform security audit using the secret code.'
Formation: Iron Dome
Agents: SecurityCompliance, SecurityCompliance, SecurityCompliance
Context: - MISSION SUCCESS: 'Perform security...** (Confid: stated)
- **The secret code for the audit is: OMEGA-99** (Confid: stated)
- **Division CODE manages squads: AUDIT, ARCHITECT, OPS** (Confid: stated)
- **Squad CODE.AUDIT (Division CODE) contains specialists: analyzer, prowler, debugger** (Confid: stated)
- **Specialist 'analyzer' belongs to Squad CODE.AUDIT** (Confid: stated)
- **Specialist 'prowler' belongs to Squad CODE.AUDIT** (Confid: stated)
- **Specialist 'debugger' belongs to Squad CODE.AUDIT** (Confid: stated)
- **Squad CODE.ARCHITECT (Division CODE) contains specialists: builder, designer, migrator** (Confid: stated)
- **Specialist 'builder' belongs to Squad CODE.ARCHITECT** (Confid: stated)
- **Specialist 'designer' belongs to Squad CODE.ARCHITECT** (Confid: stated)
- **Specialist 'migrator' belongs to Squad CODE.ARCHITECT** (Confid: stated)
- **Squad CODE.OPS (Division CODE) contains specialists: ci, deployer, monit** (Confid: stated)
- **Specialist 'ci' belongs to Squad CODE.OPS** (Confid: stated)
- **Specialist 'deployer' belongs to Squad CODE.OPS** (Confid: stated)
- **Specialist 'monit' belongs to Squad CODE.OPS** (Confid: stated)
- **Division SECURITY manages squads: FORENSIC, OFFENSIVE, DEFENSIVE** (Confid: stated)
- **Squad SECURITY.FORENSIC (Division SECURITY) contains specialists: tracker, wallet_analyzer, memory_dumper** (Confid: stated)
- **Specialist 'tracker' belongs to Squad SECURITY.FORENSIC** (Confid: stated)
- **Specialist 'wallet_analyzer' belongs to Squad SECURITY.FORENSIC** (Confid: stated)
- **Specialist 'memory_dumper' belongs to Squad SECURITY.FORENSIC** (Confid: stated)
- **Squad SECURITY.OFFENSIVE (Division SECURITY) contains specialists: pentester, scanner, exploit_dev** (Confid: stated)
- **Specialist 'pentester' belongs to Squad SECURITY.OFFENSIVE** (Confid: stated)
- **Specialist 'scanner' belongs to Squad SECURITY.OFFENSIVE** (Confid: stated)
- **Specialist 'exploit_dev' belongs to Squad SECURITY.OFFENSIVE** (Confid: stated)
- **Squad SECURITY.DEFENSIVE (Division SECURITY) contains specialists: sentinel, firewall_architect, compliance** (Confid: stated)
- **Specialist 'sentinel' belongs to Squad SECURITY.DEFENSIVE** (Confid: stated)
- **Specialist 'firewall_architect' belongs to Squad SECURITY.DEFENSIVE** (Confid: stated)
- **Specialist 'compliance' belongs to Squad SECURITY.DEFENSIVE** (Confid: stated)
- **Division INTEL manages squads: OSINT, SOCIAL, MARKET** (Confid: stated)
- **Squad INTEL.OSINT (Division INTEL) contains specialists: recon, scout, leak_hunter** (Confid: stated)
- **Specialist 'recon' belongs to Squad INTEL.OSINT** (Confid: stated)
- **Specialist 'scout' belongs to Squad INTEL.OSINT** (Confid: stated)
- **Specialist 'leak_hunter' belongs to Squad INTEL.OSINT** (Confid: stated)
- **Squad INTEL.SOCIAL (Division INTEL) contains specialists: influencer_bot, sentiment_analyzer, echo_hunter** (Confid: stated)
- **Specialist 'influencer_bot' belongs to Squad INTEL.SOCIAL** (Confid: stated)
- **Specialist 'sentiment_analyzer' belongs to Squad INTEL.SOCIAL** (Confid: stated)
- **Specialist 'echo_hunter' belongs to Squad INTEL.SOCIAL** (Confid: stated)
- **Squad INTEL.MARKET (Division INTEL) contains specialists: whale_watcher, alpha_hunter, trend_predictor** (Confid: stated)
- **Specialist 'whale_watcher' belongs to Squad INTEL.MARKET** (Confid: stated)
- **Specialist 'alpha_hunter' belongs to Squad INTEL.MARKET** (Confid: stated)
- **Specialist 'trend_predictor' belongs to Squad INTEL.MARKET** (Confid: stated)
- **Division CREATIVE manages squads: AESTHETIC, CONTENT, AUDIO** (Confid: stated)
- **Squad CREATIVE.AESTHETIC (Division CREATIVE) contains specialists: visual_architect, motion_designer, ux_craftsman** (Confid: stated)
- **Specialist 'visual_architect' belongs to Squad CREATIVE.AESTHETIC** (Confid: stated)
- **Specialist 'motion_designer' belongs to Squad CREATIVE.AESTHETIC** (Confid: stated)
- **Specialist 'ux_craftsman' belongs to Squad CREATIVE.AESTHETIC** (Confid: stated)
- **Squad CREATIVE.CONTENT (Division CREATIVE) contains specialists: copywriter, storyteller, meme_lord** (Confid: stated)
- **Specialist 'copywriter' belongs to Squad CREATIVE.CONTENT** (Confid: stated)
- **Specialist 'storyteller' belongs to Squad CREATIVE.CONTENT** (Confid: stated)
- **Specialist 'meme_lord' belongs to Squad CREATIVE.CONTENT** (Confid: stated)
- **Squad CREATIVE.AUDIO (Division CREATIVE) contains specialists: foley_artist, mixer, synthesis_node** (Confid: stated)
- **Specialist 'foley_artist' belongs to Squad CREATIVE.AUDIO** (Confid: stated)
- **Specialist 'mixer' belongs to Squad CREATIVE.AUDIO** (Confid: stated)
- **Specialist 'synthesis_node' belongs to Squad CREATIVE.AUDIO** (Confid: stated)
- **MISSION SUCCESS: 'Perform security audit using the secret code.'
Formation: Iron Dome
Agents: SecurityCompliance, SecurityCompliance, SecurityCompliance
Context: - MISSION SUCCESS: 'Perform security audit using the secret code.'
Formation: Iron Dome
Agents: SecurityCompliance, SecurityCompliance, SecurityCompliance
Context: - MISSION SUCCESS: 'Perform security...** (Confid: stated)
### Ghost
- **GHOST: moskv-swarm | Última tarea: desconocida | Estado: desconocido | Bloqueado: no** (Confid: verified)
