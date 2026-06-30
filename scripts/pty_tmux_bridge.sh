#!/usr/bin/env bash
# [C5-REAL] TMUX PTY-Bridge v2.0
# Multiplexor físico avanzado para observabilidad, control determinista y aserción de TUIs.
#
# Autor: Borja Moskv (borjamoskv)
# Licencia: Apache-2.0

set -euo pipefail

# Comprobar dependencia tmux
if ! command -v tmux &> /dev/null; then
    echo "❌ [ERROR] tmux no está instalado en el sistema host. Abortando." >&2
    exit 1
fi

COMMAND="${1:-}"
SESSION_NAME="${2:-}"

show_help() {
    echo "Uso: $0 <comando> <nombre_sesion> [args...]"
    echo ""
    echo "Comandos:"
    echo "  spawn <cmd>      Inicia una sesión desacoplada ejecutando <cmd>."
    echo "  read             Captura el buffer visual actual de la pantalla (pane viewport)."
    echo "  history          Captura todo el buffer del scrollback histórico (hasta 32k líneas)."
    echo "  dump <file>      Vuelca el buffer visual actual a un archivo físico."
    echo "  inject <keys>    Inyecta secuencias de teclas físicas o combinaciones (ej. Enter, C-c, Down)."
    echo "  send-text <txt>  Inyecta una cadena de texto literal de forma segura."
    echo "  clear            Limpia la pantalla de la TUI (inyecta C-l)."
    echo "  wait <regex> [t] Bloquea el hilo esperando que la expresión regular coincida en pantalla (timeout t seg, def: 10)."
    echo "  resize <w> <h>   Redimensiona el viewport del terminal virtual (ej. resize 120 40)."
    echo "  status           Muestra el PID de ejecución, tiempo de vida y estado de salud."
    echo "  kill             Finaliza y destruye la sesión tmux (Apoptosis celular)."
    exit 1
}

if [ -z "$COMMAND" ] || [ -z "$SESSION_NAME" ]; then
    show_help
fi

# Desplazar los primeros 2 argumentos para capturar el resto en cases
shift 2

case "$COMMAND" in
    spawn)
        EXEC_CMD="$*"
        if [ -z "$EXEC_CMD" ]; then
            echo "❌ [ERROR] Comando de ejecución vacío para spawn." >&2
            exit 1
        fi
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "⚠️ [P1] La sesión PTY '$SESSION_NAME' ya existe. Cierra (kill) antes de relanzar."
            exit 1
        fi
        # Crear sesión y forzar tamaño por defecto de 100x30 para evitar dependencias del terminal anfitrión
        tmux new-session -d -s "$SESSION_NAME" -x 100 -y 30 "$EXEC_CMD"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Ejecutando de forma desacoplada: $EXEC_CMD"
        ;;
        
    read)
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi
        tmux capture-pane -t "$SESSION_NAME" -p
        ;;

    history)
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi
        # Captura desde el inicio del scrollback (-S -32768) hasta el final (viewport)
        tmux capture-pane -S -32768 -t "$SESSION_NAME" -p
        ;;

    dump)
        FILE="${1:-}"
        if [ -z "$FILE" ]; then
            echo "❌ [ERROR] Debes especificar la ruta física del archivo (ej. dump out.txt)." >&2
            exit 1
        fi
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi
        tmux capture-pane -t "$SESSION_NAME" -p > "$FILE"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Viewport volcado en $FILE"
        ;;

    inject)
        KEY="$*"
        if [ -z "$KEY" ]; then
            echo "❌ [ERROR] No se han especificado teclas para inyectar." >&2
            exit 1
        fi
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi
        tmux send-keys -t "$SESSION_NAME" "$KEY"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Simulación física inyectó tecla(s): $KEY"
        ;;

    send-text)
        TEXT="$*"
        if [ -z "$TEXT" ]; then
            echo "❌ [ERROR] Texto vacío para inyectar." >&2
            exit 1
        fi
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi
        # Usa -l para literal
        tmux send-keys -t "$SESSION_NAME" -l "$TEXT"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Simulación física inyectó texto literal: $TEXT"
        ;;

    clear)
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi
        tmux send-keys -t "$SESSION_NAME" "C-l"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Pantalla limpiada (C-l inyectado)."
        ;;

    wait)
        PATTERN="${1:-}"
        TIMEOUT="${2:-10}"
        INTERVAL="0.1"
        
        if [ -z "$PATTERN" ]; then
            echo "❌ [ERROR] Debes especificar un patrón regex para esperar." >&2
            exit 1
        fi
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi

        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Esperando patrón regex: '$PATTERN' (Timeout: ${TIMEOUT}s)..."
        
        START_TIME=$(date +%s)
        while true; do
            # Capturar el buffer y comprobar patrón vía grep extendido
            CURRENT_TEXT=$(tmux capture-pane -t "$SESSION_NAME" -p)
            if echo "$CURRENT_TEXT" | grep -qE "$PATTERN"; then
                echo "[SUCCESS] Patrón detectado."
                exit 0
            fi
            
            CURRENT_TIME=$(date +%s)
            ELAPSED=$((CURRENT_TIME - START_TIME))
            if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
                echo "❌ [TIMEOUT] El patrón '$PATTERN' no apareció en la pantalla tras ${TIMEOUT} segundos." >&2
                exit 1
            fi
            sleep "$INTERVAL"
        done
        ;;

    resize)
        WIDTH="${1:-100}"
        HEIGHT="${2:-30}"
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "❌ [ERROR] La sesión '$SESSION_NAME' no existe." >&2
            exit 1
        fi
        # Redimensionar la ventana de la sesión
        tmux resize-window -t "$SESSION_NAME" -x "$WIDTH" -y "$HEIGHT"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Redimensionado a ${WIDTH}x${HEIGHT}."
        ;;

    status)
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "OFFLINE"
            exit 0
        fi
        # Extraer PID del shell/proceso principal de la sesión y tiempo de inicio
        PID=$(tmux list-panes -t "$SESSION_NAME" -F "#{pane_pid}")
        START_EPOCH=$(tmux list-panes -t "$SESSION_NAME" -F "#{session_created}")
        NOW=$(date +%s)
        UPTIME=$((NOW - START_EPOCH))
        echo "ONLINE | PID: $PID | Uptime: ${UPTIME}s"
        ;;

    kill)
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "⚠️ [P2] La sesión '$SESSION_NAME' no existe. Saltando terminación."
            exit 0
        fi
        tmux kill-session -t "$SESSION_NAME"
        echo "[C5-REAL] TMUX PTY [$SESSION_NAME] -> Apoptosis ejecutada (Sesión destruida)."
        ;;

    *)
        show_help
        ;;
esac
