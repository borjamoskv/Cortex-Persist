# CORTEX DEEP RESEARCH: GITHUB CODESPACES
> **Target:** `https://docs.github.com/en/codespaces`
> **Mode:** AUTODIDACT (Deep Research)
> **Reality Level:** C5-REAL
> **Confidence:** 1000/1000 (Primary Source Documentation)

## 1. INVARIANTES ESTRUCTURALES (ARQUITECTURA)
- **Topología Base:** Contenedor Docker desplegado sobre una Máquina Virtual Linux dedicada, alojada en la nube (Azure por defecto).
- **Especificaciones Físicas:** Escalable desde 2 cores / 8 GB RAM / 32 GB Storage hasta 32 cores / 128 GB RAM / 128 GB Storage.
- **Jerarquía de Directorios (Aislamiento Entrópico):**
  - `/workspaces`: Persistente. Sobrevive a la reconstrucción del contenedor. El repositorio se clona (shallow por defecto) aquí.
  - Otros directorios (ej. `~/.bashrc`, `/usr`): Efímeros por defecto. Sujetos al ciclo de vida del contenedor (se purgan en reconstrucción, salvo `/tmp` que puede persistir).
- **Punto de Entrada Causal:** `.devcontainer/devcontainer.json` o `.devcontainer.json` en la raíz. Si no existe, se utiliza la imagen base estándar de GitHub Linux.

## 2. MECÁNICA DE INGESTA Y CICLO DE VIDA (FSM)
1. **Asignación (SAGA-1):** Se aprovisiona VM + Almacenamiento. Se inyecta la imagen base Linux. Se ejecuta clon parcial (`shallow clone`) hacia `/workspaces`.
2. **Construcción (SAGA-2):** El dev container es parseado desde `.devcontainer/devcontainer.json` y `Dockerfile` (si existe). Si se usan "features" (plugins), se inyectan como capas Docker.
3. **Fijación (SAGA-3):** Se conecta vía Browser, VS Code Desktop o GitHub CLI (`gh codespaces`).
4. **Post-Construcción (SAGA-4):** Ejecución asíncrona de `postCreateCommand` (útil para inyección de dotfiles personales o Git hooks).
5. **Apoptosis Parcial:** Time-out de inactividad (default 30 min) congela el contenedor. Un-committed changes se preservan.

## 3. MOTOR DE CONFIGURACIÓN (`devcontainer.json`)
- **Naturaleza Criptográfica:** Define "customization" (requerido para compilar el proyecto) no "personalization" (preferencias del usuario).
- **Features:** Componentes atómicos inyectables (ej. Node, Python, AWS CLI) bajo el nodo `"features"`.
- **Anuladores UI:**
  - Workspace Settings: `.vscode/settings.json` o anidadas en `devcontainer.json` bajo la key `settings`.
- **Permisos y Privilegios:** El host virtual corre en un contexto que permite escalada limpia (`sudo` disponible de facto para instalar dependencias pre-compiladas no contempladas en el `devcontainer.json`).

## 4. VECTOR EXERGÉTICO (VS. LOCAL HOST)
- **Desacoplamiento Termodinámico:** Delega la disipación térmica del compilador al nodo remoto. Retiene el cliente (VS Code / Web) estrictamente como capa presentacional y puente TCP.
- **Port Forwarding Autómata:** Puertos descubiertos son mapeados automáticamente (HTTP) a URLs privadas. Se puede alterar su visibilidad (Org / Pública) explícitamente.
- **Dotfiles y Sync:** Aislamiento del individuo en el enjambre. La personalización se abstrae en el repósito de `dotfiles` del usuario y "Settings Sync", preservando la pureza de `.devcontainer/devcontainer.json` para el equipo.

> **Ontology Forge:** 1 Invariante Architectural Confirmado. Codespaces colapsa la entropía de entornos de desarrollo cruzados en un único Grafo FSM determinista liderado por `devcontainer.json`.
