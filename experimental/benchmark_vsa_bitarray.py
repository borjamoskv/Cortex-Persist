"""CORTEX v7 — HDC Bitwise Representation Benchmarking.

Compares:
1. Bipolar int8 (Current implementation: 8000 bytes per HV)
2. NumPy uint64 Bit Array (125 uint64s, using np.bitwise_xor)
3. Pure Python list of uint64s (125 elements, using ^ and bit_count)
4. Pure Python single giant integer (8000-bit int, using ^ and bit_count)

Declaración de Realidad: C5-REAL (Benchmarking real ejecutado localmente)
"""

import time
import sys
import array
import random
import numpy as np

DIM = 8000
NUM_OPS = 100000  # Number of operations to test for speed
UINT64_COUNT = DIM // 64  # 125 elements

print("=" * 60)
print(f"VSA-SDM BENCHMARKING: DIM={DIM}, OPS={NUM_OPS}")
print("=" * 60)

# --- 1. CURRENT BIPOLAR NP.INT8 ---
def make_bipolar():
    return np.random.choice(np.array([-1, 1], dtype=np.int8), size=DIM)

a_bip = make_bipolar()
b_bip = make_bipolar()

# Measure Bipolar Bind
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    res_bip = np.multiply(a_bip, b_bip, dtype=np.int8)
t_bip_bind = time.perf_counter() - t0

# Measure Bipolar Similarity
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    dot = int(np.dot(a_bip.astype(np.int32), b_bip.astype(np.int32)))
    sim_bip = dot / DIM
t_bip_sim = time.perf_counter() - t0

mem_bip = a_bip.nbytes + sys.getsizeof(a_bip)


# --- 2. NUMPY UINT64 BIT ARRAY ---
def make_np_uint64():
    return np.random.randint(0, 2**64, size=UINT64_COUNT, dtype=np.uint64)

a_np64 = make_np_uint64()
b_np64 = make_np_uint64()

# Measure NumPy uint64 Bind
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    res_np64 = np.bitwise_xor(a_np64, b_np64)
t_np64_bind = time.perf_counter() - t0

# Measure NumPy uint64 Similarity
# We need to count bits. NumPy doesn't have a direct popcount on uint64 until recent versions,
# so we do a standard lookup or map to Python ints. Let's see the speed when casting to python or using bit_count.
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    xor_res = np.bitwise_xor(a_np64, b_np64)
    # Cast to python elements to use bit_count
    popcnt = sum(int(x).bit_count() for x in xor_res)
    sim_np64 = 1.0 - (popcnt / DIM)
t_np64_sim = time.perf_counter() - t0

mem_np64 = a_np64.nbytes + sys.getsizeof(a_np64)


# --- 3. PURE PYTHON LIST OF UINT64s ---
def make_py_list():
    return [random.getrandbits(64) for _ in range(UINT64_COUNT)]

a_pylist = make_py_list()
b_pylist = make_py_list()

# Measure Pure Python List Bind
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    res_pylist = [x ^ y for x, y in zip(a_pylist, b_pylist)]
t_pylist_bind = time.perf_counter() - t0

# Measure Pure Python List Similarity
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    popcnt = sum((x ^ y).bit_count() for x, y in zip(a_pylist, b_pylist))
    sim_pylist = 1.0 - (popcnt / DIM)
t_pylist_sim = time.perf_counter() - t0

# Size of 125 integers in a list
mem_pylist = sys.getsizeof(a_pylist) + sum(sys.getsizeof(x) for x in a_pylist)


# --- 4. PURE PYTHON GIANT INTEGER ---
def make_giant_int():
    return random.getrandbits(DIM)

a_giant = make_giant_int()
b_giant = make_giant_int()

# Measure Giant Int Bind
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    res_giant = a_giant ^ b_giant
t_giant_bind = time.perf_counter() - t0

# Measure Giant Int Similarity
t0 = time.perf_counter()
for _ in range(NUM_OPS):
    popcnt = (a_giant ^ b_giant).bit_count()
    sim_giant = 1.0 - (popcnt / DIM)
t_giant_sim = time.perf_counter() - t0

mem_giant = sys.getsizeof(a_giant)


# --- PRINT RESULTS ---
print(f"{'Method':<30} | {'Bind (s)':<12} | {'Similarity (s)':<15} | {'Memory (bytes)':<15}")
print("-" * 80)
print(f"{'1. Bipolar np.int8 (Current)':<30} | {t_bip_bind:<12.5f} | {t_bip_sim:<15.5f} | {mem_bip:<15}")
print(f"{'2. NumPy uint64 Bit Array':<30} | {t_np64_bind:<12.5f} | {t_np64_sim:<15.5f} | {mem_np64:<15}")
print(f"{'3. Python List[uint64]':<30} | {t_pylist_bind:<12.5f} | {t_pylist_sim:<15.5f} | {mem_pylist:<15}")
print(f"{'4. Python Giant Int (8000-bit)':<30} | {t_giant_bind:<12.5f} | {t_giant_sim:<15.5f} | {mem_giant:<15}")
print("=" * 80)

# Verify Mathematical Equivalence (Check similarity mapping)
# Map bipolar to binary: (1 - val) // 2
a_bin_mapped = (1 - a_bip) // 2
b_bin_mapped = (1 - b_bip) // 2

# Pack mapped bipolar into a giant integer
giant_a_mapped = 0
for idx, val in enumerate(a_bin_mapped):
    if val == 1:
        giant_a_mapped |= (1 << idx)

giant_b_mapped = 0
for idx, val in enumerate(b_bin_mapped):
    if val == 1:
        giant_b_mapped |= (1 << idx)

# Check cosine similarity vs Hamming similarity of giant ints
dot = int(np.dot(a_bip.astype(np.int32), b_bip.astype(np.int32)))
cos_sim = dot / DIM

popcnt_mapped = (giant_a_mapped ^ giant_b_mapped).bit_count()
ham_sim = 1.0 - (popcnt_mapped / DIM)

# Expected relationship: cos_sim = 2 * ham_sim - 1
reconstructed_cos = 2 * ham_sim - 1
print(f"Cosine Similarity (Bipolar):           {cos_sim:.6f}")
print(f"Hamming Similarity (Giant Int):        {ham_sim:.6f}")
print(f"Reconstructed Cosine from Hamming:     {reconstructed_cos:.6f}")
assert abs(cos_sim - reconstructed_cos) < 1e-9, "Equivalence validation failed!"
print("✅ Mathematical equivalence validated successfully.")
print("=" * 80)
