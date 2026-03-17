# MEJORAlo (CORTEX Engine Extension)

MEJORAlo is the Sovereign CORTEX **X-Ray Diagnostic and Healing Engine**. It evaluates the health, complexity, and thermodynamic stability of the codebase across 14 distinct dimensions, producing a comprehensive `0-100` score.

## Core Philosophical Axiom
A static code scanner is structurally blind to environmental friction. MEJORAlo isolates project technical debt from host environmental degradation by capturing live system telemetry alongside AST and dependency parsing.

## The 14D X-Ray Scan

MEJORAlo analyzes the project via 14 distinct diagnostic vectors:

1. **AST Complexity:** Deep nesting, cyclomatic complexity limits.
2. **Dead Code:** Unused imports, orphaned functions (Ghost isolation).
3. **Type Strictness:** Enforced via Pyright.
4. **Linting:** Enforced via Ruff (`E`, `F`, `W`, `B`, `ASYNC`, `UP`).
5. **Psi Density (TODO/FIXME):** Tracks unresolved cognitive debt.
6. **No-Blocking I/O:** Async-first enforcement, punishing `time.sleep` or synchronous HTTP in event loops.
7. **Security (Privacy Shield):** Scans for exposed secrets, API keys, or hardcoded credentials.
8. **Dependency Entropy:** Bloat detection.
9. **Event Loop Safety:** Ensure generators and closures do not capture late bindings improperly.
10. **Test Coverage:** Enforces minimum structural test density.
11. **Boundary Adherence:** API contracts and `__all__` encapsulations.
12. **Exception Handling:** Flags blanket `except Exception` or silent `pass`.
13. **Industrial Noir Standards:** Code style alignment with CORTEX aesthetics.
14. **Control macOS (Telemetry):** Environmental Host awareness (Active on `darwin`).

## Control macOS (Telemetry Edition)

On macOS systems, MEJORAlo introduces a semantic environment scanner (`mac_control.py`) to prevent penalizing developers for host-level degradation. This module uses zero Python dependencies, exclusively leveraging native macOS Unix binaries (`sysctl`, `top`, `vm_stat`, `pmset`, `ioreg`, `ps`, `osascript`).

### MacSnapshot Signals

| Signal | Source | Penalty | Heuristic Impact |
|:---|:---|:---|:---|
| **Memory Pressure** | `sysctl`, `vm_stat` | `-20` to `-40` | Discards false positive "memory leak" alerts if host is swapping. |
| **Process Entropy** | `ps -A` | `-5` per 10 > 250 | Detects daemon sprawl and zombie processes. |
| **Thermal State** | `pmset`, `ioreg` | `-10` to `-40` | Marks timing/latency benchmarks as unreliable if throttling is active. |
| **Accessibility (AX)** | `osascript` | `-25` | Blocks UI automation. Requires immediate permission grant. |
| **CPU Saturation** | `top -l 1` | Scaled | Sustained >90% flags tests as unrepresentative. |

> **Graceful Degradation:** If `sys.platform != "darwin"`, MEJORAlo gracefully degrades to a neutral score (`100/100`) for this dimension, ensuring Linux/Windows users are not penalized for unsupported telemetry.

## Quick CLI Usage

You can run the full X-Ray scan:
```bash
cortex mejoralo scan <project_dir>
```

Or interrogate the host operating system directly (macOS only):
```bash
cortex mejoralo system
# or directly in code: engine.mac_inspect()
```

## Documentation Reference
See [RFC: MEJORAlo Mac Telemetry](../../../docs/MEJORALO-MAC-TELEMETRY-RFC.md) for the detailed causal matrix and architectural thesis for this capability.
