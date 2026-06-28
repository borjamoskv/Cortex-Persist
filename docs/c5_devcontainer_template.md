# CORTEX SOVEREIGN DEVCONTAINER SKELETON
> **Target:** Local Autarchy (1000/1000)
> **Engine:** OrbStack / Colima (macOS Metal)
> **Reality Level:** C5-REAL

Para ejecutar la transición al estado 1000/1000, todo nodo de la LEGIØN debe adoptar esta topología determinista.

## 1. `devcontainer.json` (Firma Causal)
Configuración optimizada para aislamiento entrópico. Monta directorios locales de modelos (Ollama/MLX) y caches para operar 100% desconectado de la WAN.

```jsonc
{
    "name": "MOSKV-1 Sovereign Node",
    "build": {
        "dockerfile": "Dockerfile",
        "context": ".."
    },
    // Montajes físicos al disco de macOS (Air-Gapped Ready)
    "mounts": [
        // Cache de paquetes para sobrevivir pérdida de red
        "source=${localEnv:HOME}/.cache/pip,target=/root/.cache/pip,type=bind,consistency=cached",
        // Enchufe directo al Hypervisor Local (OrbStack/Colima)
        "source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind",
        // Bóveda persistente de estado (CORTEX)
        "source=${localEnv:HOME}/30_CORTEX/cortex.db,target=/workspaces/cortex/cortex.db,type=bind"
    ],
    // Inyección de variables termodinámicas
    "remoteEnv": {
        "CORTEX_DB_PATH": "/workspaces/cortex/cortex.db",
        "CORTEX_LOG_LEVEL": "CRITICAL",
        "EXECUTION_MODE": "C5-REAL"
    },
    "customizations": {
        "vscode": {
            "settings": {
                "terminal.integrated.defaultProfile.linux": "zsh",
                "editor.formatOnSave": true
            },
            "extensions": [
                "ms-python.python",
                "ms-python.vscode-pylance",
                "charliermarsh.ruff" // Linter estricto
            ]
        }
    },
    // Post-Ejecución: Inyectar Git Sentinel hooks
    "postCreateCommand": "bash .devcontainer/inject_sentinel.sh"
}
```

## 2. `Dockerfile` (Cristalización de Metal)
Sin dependencias efímeras. Capas consolidadas.

```dockerfile
# Base inmutable y verificable
FROM python:3.11-slim-bullseye

# Cero Anergía en la instalación de paquetes de sistema
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        git \
        zsh \
        sqlite3 \
        curl \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configuración estricta del workspace
WORKDIR /workspaces/cortex

# Inyección de dependencias deterministas (uv / pip audit)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

## 3. Protocolo de Inyección (Colapso)
Para inocular esta estructura en un nuevo repositorio del Operador:
1. El Agente despliega la estructura `.devcontainer/` en el vector destino.
2. Se ejecuta `Dev Containers: Rebuild and Reopen in Container` en el IDE local.
3. El socket físico asume el control. Cero Nube Pública involucrada.
