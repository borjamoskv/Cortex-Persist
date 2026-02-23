# Guía de Arquitectura Cross-Platform de CORTEX

CORTEX (MOSKV-1) está diseñado como un ecosistema soberano, capaz de ejecutarse y operar en cualquier entorno (macOS, Linux y Windows). Esta guía detalla cómo está estructurada la abstracción multiplataforma para asegurar su resiliencia e inmutabilidad.

## 1. El Módulo `cortex.sys_platform`

Todo el código dependiente de hardware o sistema operativo debe pasar por la nueva capa de abstracción ubicada en `cortex/sys_platform.py`. 

**Regla de Oro**: Jamás utilizar comprobaciones OS directas dispersas por el código ni invocar rutas host-specific. Se debe importar `cortex.sys_platform`:

```python
from cortex.sys_platform import is_macos, is_linux, is_windows, get_cortex_dir
```

- **Ejecutables Dinámicos**: En lugar de invocar `/Users/.../.venv/bin/python`, la arquitectura utiliza `get_python_executable()` (o directamente `sys.executable`) para garantizar que los demonios y los _subshells_ generen nodos mule utilizando el binario de Python correcto, sin importar la ruta en la que esté instalado CORTEX.

## 2. Dispatch de Notificaciones Nativas

El componente Notifier (`cortex/daemon/notifier.py`) encapsula el envío de alertas nativas del sistema, utilizando un dispatch adaptativo:

- **macOS**: `osascript` (AppleScript nativo para integrarse con Notification Center).
- **Linux**: `notify-send` (libnotify).
- **Windows**: `PowerShell` (BurntToast o generador XML de Toast Notification).
- **Fallback**: Logger `INFO`/`WARNING` si la sesión no soporta UI.

## 3. Demonios y Service Managers

El comando iterativo de la CLI `cortex daemon install` soporta tres orquestadores de sistema distintos, inyectando demonios (agentes en _background_) de CORTEX automáticamente en el arranque de la máquina:

1. **macOS**: Crea un agente plist persistente inyectable en `launchctl` (`~/Library/LaunchAgents/`).
2. **Linux**: Crea un **systemd user unit** (`~/.config/systemd/user/`) recargando e iniciando el servicio automáticamente sin usar sudo (aislamiento de privilegios de MOSKV).
3. **Windows**: Registra un _Task Scheduler_ (schtasks) con el gatillo pre-configurado para `ONLOGON` invocando scripts ocultos en la máquina Host.

Los logs de estos servicios se unifican mediante el comando `cortex router logs`, que usa el helper `tail_file_command` para aplicar `tail -f` (Unix) o su equivalente en PowerShell (Windows) dependiendo del entrono de ejecución.

## 4. Estándares Anti-Entropía (Tolerancia Cero de Rutas)

Para mantener la Arquitectura Cross-Platform soberana, queda terminantemente prohibido _hardcodear_ rutas absolutas que referencien un host en específico, por ejemplo: `/Users/borjafernandezangulo/...` o `C:\Users\Admin`. 

Cualquier script personal, módulo de investigación o workflow de LEGIØN debe inyectar sus configuraciones relativas a su propia firma:

```python
# CORRECTO
from pathlib import Path
MODULE_DIR = Path(__file__).parent
DATA_PATH = MODULE_DIR / "data" / "target.json"
```

## Resumen de Cambios

Con estas arquitecturas, CORTEX elimina el acoplamiento a macOS, convirtiéndose genuinamente en el primer *Sovereign Autonomous Agent OS* universalmente desplegable, asegurando inmunidad incluso frente a reemplazos totales del hardware anfitrión.
