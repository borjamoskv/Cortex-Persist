#!/bin/zsh

# VSA-LINKER v1.1 | AG-2026-CORTEX
# Sovereign Command Interception & Hyperdimensional Persistence
# CITATIONS: [Kanerva '88] SDM | [Packer '23] MemGPT | [Yao '22] ReAct

vsa_preexec() {
    # 1. Escudo de Exergía (Audit Preventivo <8ms)
    # Si detecta riesgo crítico (exit 1), abortamos la ejecución.
    if ! python3 /Users/borjafernandezangulo/10_PROJECTS/exergy_shield.py "$1"; then
        # El script ya imprimió el aviso. Abortamos.
        return 1
    fi

    # 2. VSA Bind (Persistencia Hiperdimensional)
    if [[ "$1" == *"vsa-bind"* ]]; then return; fi
    (python3 /Users/borjafernandezangulo/.gemini/antigravity/skills/vsa-sdm-memory-omega/scripts/vsa_cli.py /vsa-bind "$1" &)
}


# Inyectar hook de pre-ejecución
autoload -Uz add-zsh-hook
add-zsh-hook preexec vsa_preexec

# Alias de acceso rápido
alias vsa-recall="python3 /Users/borjafernandezangulo/.gemini/antigravity/skills/vsa-sdm-memory-omega/scripts/vsa_cli.py /vsa-recall"
