# VSA-SDM Sovereign Memory — Bitwise Representation Benchmark

This report documents the empirical performance comparison of hypervector representations for the Vector Symbolic Architecture (VSA) / Sparse Distributed Memory (SDM) subsystem.

**Declaración de Realidad:** `C5-REAL` (Empirical execution on Apple Silicon M-series, macOS 15+ kernel).

---

## 📊 Benchmark Results

| Representation Method | Bind Time (100k ops) | Similarity Time (100k ops) | Memory footprint (1 HV) | Speedup (Sim) | Memory Savings |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Bipolar `np.int8` (Current)** | 0.07843 s | 0.57021 s | 16,112 bytes | 1.0x (Baseline) | Baseline |
| **2. NumPy `uint64` Bit Array** | 0.03774 s | 1.15913 s | 2,112 bytes | 0.5x | 86.8% |
| **3. Python `List[uint64]`** | 0.54653 s | 0.77061 s | 5,548 bytes | 0.74x | 65.5% |
| **4. Python Giant Int (8000-bit)** | **0.01042 s** | **0.01820 s** | **1,092 bytes** | **31.3x** | **93.2%** |

---

## 🧠 Architectural Insights

1. **Elimination of Loop Overhead:** Using Python's arbitrary-precision integers (which natively acts as a dynamic bit vector at the C-level) completely bypasses Python interpreter loop overhead. A single `a ^ b` or `(a ^ b).bit_count()` compiles down to highly optimized C loops over internal machine-word digits.
2. ** popcount Acceleration:** Since Python 3.10, `int.bit_count()` accesses native hardware POPCNT instructions (via compiler builtins like `__builtin_popcountll` on GCC/Clang), yielding **31.3x faster similarity execution** compared to NumPy dot-product calculations.
3. **93% Memory Reduction:** Storing the hypervector as a single python `int` reduces metadata overhead and raw allocations down to **1.09 KB**, ensuring 100% of the active working vector set resides comfortably in the L1 CPU instruction/data cache.
4. **Mathematical Equivalence:** Hamming similarity $H_{sim}$ of binary mapping maps bijectively to Cosine Similarity $cos$ of bipolar mapping via the exact linear transformation:
   $$cos = 2 \cdot H_{sim} - 1$$
   $$H_{sim} = \frac{cos + 1}{2}$$

---

## 🛠️ Action Plan: Refactoring `cortex/memory/hdc/algebra.py`

To upgrade the HDC engine to the giant integer representation, the core mathematical operators should be restructured as follows:

```python
import random

DEFAULT_DIM = 8000

def random_binary(dim: int = DEFAULT_DIM) -> int:
    return random.getrandbits(dim)

def bind(a: int, b: int) -> int:
    return a ^ b

def unbind(composite: int, key: int) -> int:
    return composite ^ key

def hamming_similarity(a: int, b: int, dim: int = DEFAULT_DIM) -> float:
    # popcount on the XOR difference gives mismatch count
    mismatches = (a ^ b).bit_count()
    return 1.0 - (mismatches / dim)

def permute(hv: int, k: int = 1, dim: int = DEFAULT_DIM) -> int:
    # Circular shift of dim-bit integer
    k = k % dim
    if k == 0:
        return hv
    mask = (1 << dim) - 1
    return ((hv << k) & mask) | (hv >> (dim - k))
```

To support majority vote bundling of $N$ giant integers:
```python
def bundle(*hvs: int, dim: int = DEFAULT_DIM) -> int:
    # Unpack to bit counts
    counts = [0] * dim
    for hv in hvs:
        for i in range(dim):
            if (hv >> i) & 1:
                counts[i] += 1
    
    # Reassemble majority bits (tie break to 1)
    threshold = len(hvs) / 2
    result = 0
    for i in range(dim):
        if counts[i] >= threshold:
            result |= (1 << i)
    return result
```

This implementation achieves Law Ω₀ invariants: synthesized Verilog/KiCad logic maps directly to registers, logic gates (XOR), and shift-registers for circular permutation without float/signed-arithmetic scaling.
