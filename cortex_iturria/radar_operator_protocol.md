# 📡 RADAR-Ω Sanity Check Protocol

> El eslabón humano no aporta entropía creativa, solo termodinámica resolutiva. RADAR vigila 24/7 y empaqueta la realidad en cold-storage. El humano verifica y mutila.

Este es tu protocolo de revisión manual para procesar los datos capturados por el 24/7 `crond/launchd` daemon. Esta es la fase manual del ciclo Ouroboros.

## 1. Abrir la Bóveda de Reportes
El sistema guarda silenciosamente radiografías topográficas del RADAR cada 6 horas en tu bóveda `radar_vault`. Para revisar los reportes:

```bash
# Entra en CORTEX
cd ~/cortex

# 1. Monta la bóveda usando la skill boveda-1 (requiere password)
# Si perdiste o no copiaste el password que se generó, búscalo en tu Keychain como "radar_vault".
/boveda mount radar_vault

# 2. Revisa los últimos escaneos del radar
ls -al /Volumes/radar_vault/
cat /Volumes/radar_vault/radar_report_*.log | tail -n 50
```

## 2. Poda de Entropía (Human Decision)
Tras revisar los logs, si detectas proliferación de fantasmas (ID ghosts con más de `0.35` de resonancia) o una Banda E (Entropía CORTEX) alarmante que no se purga biológicamente:

```bash
# Eres el ejecutor final. Limpia el árbol físico.
cortex radar prune
```

## 3. Cerrar la Bóveda y Abandonar
Inmediatamente y sin excusas.

```bash
/boveda unmount radar_vault
```
