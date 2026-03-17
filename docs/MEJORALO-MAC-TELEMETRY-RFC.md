# RFC: MEJORAlo Mac Telemetry (mac_control)

**Status:** Implemented (v8.0)  
**Author:** Sovereign CORTEX (Antigravity-Omega)  
**Context:** MEJORAlo X-Ray engine extension  

---

## 1. Thesis
A static code scanner is structurally blind to environmental friction. By injecting native macOS telemetry (`mac_control`) into MEJORAlo, we upgrade it from a passive code analyzer to an active, context-aware diagnostic engine. 

The goal is not generic observability. The goal is **causal isolation**: decoupling project technical debt from host environmental degradation.

## 2. The Data Contract: `MacSnapshot`

The raw telemetry is strictly separated from inferred findings to prevent conflating observed state with diagnostic opinion.

```python
@dataclass
class MacSnapshot:
    platform: str          # "darwin" or "unsupported"
    cpu_percent: float     # 0.0-100.0
    memory_pressure: str   # "ok" | "warn" | "critical"
    thermal_state: str     # "Nominal" | "Fair" | "Serious" | "Critical"
    process_count: int     # Running process entropy
    ax_trusted: bool       # Accessibility bridge integrity
    gpu_active: bool       # Metal / discrete GPU load
    timestamp: str         # ISO8601 UTC observation window
```

**Guards & Degradation:**
* If `sys.platform != "darwin"`, the module degrades gracefully to `platform="unsupported"`, producing a neutral score (`100`) to prevent penalizing non-Mac engineers.
* All parsing logic includes robust `try/except` fallbacks heavily preferring `Nominal` or `0.0` over runtime crashes.

## 3. Signal Extraction Methodology (Zero-Dependency)

The `mac_control` module adheres to the **mac-maestro-omega** architecture: extracting rich state using *only* pre-installed Unix/macOS binaries. No `psutil` or external C-extensions are permitted.

| Metric | Source Binary | Heuristic |
| :--- | :--- | :--- |
| **CPU %** | `top -l 1` | Parses `CPU usage:` extracting `idle` and computing `100 - idle`. |
| **Memory Pressure** | `sysctl`, `vm_stat` | Reads `vm.memory_pressure`. Fallback: extrapolates from `pageouts`. |
| **Thermal State** | `ioreg`, `pmset` | Scans `IOPlatformExpertDevice` for throttling status. |
| **Process Entropy** | `ps -A` | Counts total active PIDs to measure daemon sprawl. |
| **AX Trust** | `osascript` | Attempts to query `System Events`. Rejection implies broken automation bridge. |
| **GPU Active** | `ioreg` | Checks `IOPCIDevice` for discrete AMD/Apple hardware engagement. |

## 4. Taxonomy of Findings

Telemetry findings are categorically distinct from standard AST or dependency findings. They are classified into a specific local-friction taxonomy:

| Category | Description | Example Finding | Penalty |
| :--- | :--- | :--- | :--- |
| **Host_Runtime** | CPU/Memory saturation | *Memory pressure CRITICAL* | -20 to -40 |
| **OS_Control_Plane** | OS-level permissions | *AX trust not granted* | -25 |
| **Thermal_Physics** | Hardware throttling | *Serious thermal state* | -10 to -40 |
| **Local_Entropy** | Daemon/Process sprawl | *Process entropy high (300)* | -5 per 10 over limit |

## 5. Causal Matrix: Telemetry vs. Diagnostics

How `mac_control` signals directly alter the interpretation of standard MEJORAlo findings (Future cross-causal rules).

| macOS Telemetry Signal | Causal Impact on Code Diagnostics | Recommended System Action |
| :--- | :--- | :--- |
| **High Memory Pressure** | Degrades confidence in "slow test suite" or "memory leak" code findings. The host is swapping heavily; the code may be fine. | Mask performance-related warnings. Advise user to restart Docker/IDE. |
| **AX Trust Missing** | Explains why e2e UI tests, AppleScript, or Phantom interaction pipelines are failing. | Flag as `CRITICAL` blocker. Inject explicit instructions to open System Settings. |
| **Thermal Throttling (Serious)** | Invalidates local benchmarking. Any `time.sleep()` or async latency measurements are currently compromised by the OS scheduler. | Mark timing-based test results as `UNRELIABLE`. |
| **Process Entropy > 250** | Indicates systemic environmental decay (zombie node processes, orphaned workers). | Suggest a `killall` cleanup before evaluating background daemons in the stack. |
| **Sustained CPU > 90%** | Systemic saturation. Prevents accurate assessment of the project's baseline computational footprint. | Pause heavy static analysis (e.g., AST parsing deep trees) until thermal/CPU returns to Nominal. |

## 6. Evolution Path

**v1 (Current):** Contextual telemetry injected as an isolated scoring dimension. Findings are informative.  
**v2:** Cross-causal masking. If memory pressure is critical, auto-downgrade performance-related codebase findings so the developer isn't chasing phantom bottlenecks.  
**v3:** Temporal normalization. Instead of evaluating a single snapshot, `mac_control` will monitor a rolling 3-minute window to filter out transient spikes from sustained structural degradation. 
