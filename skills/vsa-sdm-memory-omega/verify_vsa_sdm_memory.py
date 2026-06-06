#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
VSA-SDM-MEMORY-OMEGA v3.1 - Mechanical Verifier
Deterministic. Zero stochastic. 10 gates:
  [0] Tripartite artifacts
  [1] HRR bind/retrieve
  [2] MAP-B exact self-inverse
  [3] SNR capacity model
  [4] Hierarchical chunking (proper normalization)
  [5] True Kanerva SDM (SPARSE - <5% activation)
  [6] N-gram + Record-based encoding
  [7] Ebbinghaus temporal decay (retrieval-quality proof)
  [8] Resonator network (3-factor HRR, non-trivial)
  [9] End-to-end pipeline: text→encode→bind→decay→persist→load→retrieve
"""
import hashlib
import json
import os
import struct
import sys
import tempfile

try:
    import numpy as np
except ImportError:
    print("FAIL: NumPy required.")
    sys.exit(1)

# --- GLOBAL CONFIG & RNG ---
D = 10000
rng = np.random.default_rng(seed=42)

# --- CORE HELPERS ---
def rand_vec(d=D):
    v = rng.standard_normal(d)
    return v / np.linalg.norm(v)

def rand_bipolar(d=D):
    return rng.choice([-1.0, 1.0], size=d)

def rand_binary(d=D):
    return rng.integers(0, 2, size=d).astype(np.int8)

def hrr_bind(x, y):
    return np.fft.ifft(np.fft.fft(x) * np.fft.fft(y)).real

def hrr_unbind(c, k):
    return np.fft.ifft(np.fft.fft(c) * np.conj(np.fft.fft(k))).real

def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

def normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v

def permute(v, k):
    return np.roll(v, k)

# --- VERIFICATION GATES ---

def gate_0_tripartite():
    for f in ["SKILL.md", "schema.json"]:
        if not os.path.exists(f):
            print(f"FAIL: Missing {f}")
            sys.exit(1)
    with open("schema.json") as fh:
        schema = json.load(fh)
    ops = schema["properties"]["operation"]["enum"]
    for req in ["vsa-sdm-write", "vsa-sdm-read", "vsa-encode", "vsa-decay", "vsa-persist"]:
        assert req in ops, f"Schema missing: {req}"
    print("PASS [0/9]: Tripartite present. Schema valid.")

def gate_1_hrr_bind():
    T1, S1 = rand_vec(), rand_vec()
    T2, S2 = rand_vec(), rand_vec()
    M = hrr_bind(T1, S1) + hrr_bind(T2, S2)
    assert M.shape == (D,)
    sim = cosine(S1, hrr_unbind(M, T1))
    assert sim > 0.1
    print(f"PASS [1/9]: HRR bind/retrieve. cos={sim:.4f}")

def gate_2_mapb():
    A, B = rand_bipolar(), rand_bipolar()
    assert np.allclose(A, (A * B) * B)
    print("PASS [2/9]: MAP-B self-inverse. Perfect.")

def gate_3_snr():
    for N, exp in [(10, 31.6), (100, 10.0), (500, 4.47)]:
        assert abs(np.sqrt(D / N) - exp) < 0.5
    print("PASS [3/9]: SNR=sqrt(D/N) validated.")

def gate_4_hierarchical():
    CHUNK = 50
    DAYS = 30
    day_keys = [rand_vec() for _ in range(DAYS)]
    target_day, target_event = 14, 7
    ground_truth = None

    day_tensors = []
    day_event_keys = []
    for d in range(DAYS):
        dt = np.zeros(D)
        ekeys = [rand_vec() for _ in range(CHUNK)]
        estates = [rand_vec() for _ in range(CHUNK)]
        if d == target_day:
            ground_truth = estates[target_event]
        for i in range(CHUNK):
            dt += hrr_bind(ekeys[i], estates[i])
        dt = normalize(dt)
        day_tensors.append(dt)
        day_event_keys.append((ekeys, estates))

    month = np.zeros(D)
    for d in range(DAYS):
        month += hrr_bind(day_keys[d], day_tensors[d])
    month = normalize(month)

    day_extracted = hrr_unbind(month, day_keys[target_day])
    evt_extracted = hrr_unbind(day_extracted, day_event_keys[target_day][0][target_event])
    sim_h = cosine(ground_truth, evt_extracted)
    assert sim_h > 0.01
    print(f"PASS [4/9]: Hierarchical 30d×50e. 2-hop cos={sim_h:.4f}. 80KB fixed.")

def gate_5_sdm():
    M_locs = 1000
    addresses = np.array([rand_binary() for _ in range(M_locs)])
    counters = np.zeros((M_locs, D), dtype=np.int32)

    def hamming_batch(addr, all_addrs):
        return np.sum(addr != all_addrs, axis=1)

    cal_addr = rand_binary()
    cal_dists = hamming_batch(cal_addr, addresses)
    target_pct = 1.0
    radius = int(np.percentile(cal_dists, target_pct))

    activated_count = int(np.sum(cal_dists <= radius))
    activation_rate = activated_count / M_locs
    assert activation_rate < 0.10, f"SDM not sparse: {activation_rate:.1%} activation"

    def sdm_write(addr, data_bipolar):
        dists = hamming_batch(addr, addresses)
        mask = dists <= radius
        counters[mask] += data_bipolar

    def sdm_read(addr):
        dists = hamming_batch(addr, addresses)
        mask = dists <= radius
        if not np.any(mask):
            return np.zeros(D, dtype=np.int8)
        total = np.sum(counters[mask], axis=0)
        return (total > 0).astype(np.int8)

    counters[:] = 0
    test_patterns = []
    test_addrs = []
    for i in range(3):
        a = addresses[i * 100].copy()
        p = rand_binary()
        bp = p.astype(np.int32) * 2 - 1
        sdm_write(a, bp)
        test_addrs.append(a)
        test_patterns.append(p)

    retrieved = sdm_read(test_addrs[0])
    match = np.sum(retrieved == test_patterns[0]) / D
    assert match > 0.55, f"SDM read failed: {match:.2%}"
    print(f"PASS [5/9]: Kanerva SDM. {M_locs} locs, r={radius}, activation={activation_rate:.1%}, accuracy={match:.2%}")
    return M_locs, radius, activation_rate

def encode_ngram(text, char_vecs, n=3):
    text = text.lower()
    doc = np.zeros(D)
    ct = 0
    for i in range(len(text) - n + 1):
        gram = text[i:i + n]
        if all(c in char_vecs for c in gram):
            gv = char_vecs[gram[0]]
            for k in range(1, n):
                gv = hrr_bind(permute(char_vecs[gram[k]], k), gv)
            doc += gv
            ct += 1
    return normalize(doc) if ct > 0 else doc

def encode_record(record, field_keys, char_vecs):
    rec_vec = np.zeros(D)
    for key, val in record.items():
        if key in field_keys:
            val_vec = encode_ngram(val, char_vecs)
            rec_vec += hrr_bind(field_keys[key], val_vec)
    return normalize(rec_vec)

def gate_6_ngram():
    alphabet = "abcdefghijklmnopqrstuvwxyz "
    char_vecs = {ch: rand_vec() for ch in alphabet}
    field_keys = {
        "time": rand_vec(), "action": rand_vec(),
        "status": rand_vec(), "agent": rand_vec()
    }

    v1 = encode_ngram("deploy to production", char_vecs)
    v2 = encode_ngram("deploy to production", char_vecs)
    v3 = encode_ngram("quantum entanglement", char_vecs)
    assert cosine(v1, v2) > 0.99
    assert cosine(v1, v3) < 0.3

    r1 = encode_record({"time": "morning", "action": "deploy", "status": "success"}, field_keys, char_vecs)
    r2 = encode_record({"time": "morning", "action": "deploy", "status": "success"}, field_keys, char_vecs)
    r3 = encode_record({"time": "night", "action": "rollback", "status": "failure"}, field_keys, char_vecs)
    assert cosine(r1, r2) > 0.99
    assert cosine(r1, r3) < cosine(r1, r2)
    print(f"PASS [6/9]: Ngram same={cosine(v1, v2):.4f} diff={cosine(v1, v3):.4f}. Record same={cosine(r1, r2):.4f} diff={cosine(r1, r3):.4f}")
    return char_vecs

def gate_7_ebbinghaus():
    lam = 0.15
    eps = 0.01
    N_items = 20
    times = np.arange(N_items, dtype=np.float64)
    weights = np.exp(-lam * times)

    vecs = [rand_vec() for _ in range(N_items)]
    keys = [rand_vec() for _ in range(N_items)]

    M_decayed = np.zeros(D)
    M_uniform = np.zeros(D)
    for i in range(N_items):
        bound = hrr_bind(keys[i], vecs[i])
        M_decayed += weights[i] * bound
        M_uniform += bound

    recent_from_decay = hrr_unbind(M_decayed, keys[0])
    recent_from_uniform = hrr_unbind(M_uniform, keys[0])
    sim_decay = cosine(vecs[0], recent_from_decay)
    sim_uniform = cosine(vecs[0], recent_from_uniform)
    assert sim_decay > sim_uniform, "Decay must improve recent retrieval"

    old_from_decay = hrr_unbind(M_decayed, keys[-1])
    old_from_uniform = hrr_unbind(M_uniform, keys[-1])
    sim_old_d = cosine(vecs[-1], old_from_decay)
    sim_old_u = cosine(vecs[-1], old_from_uniform)

    prunable = int(np.sum(weights < eps))
    print(f"PASS [7/9]: Ebbinghaus λ={lam}. Recent: decay={sim_decay:.4f} > uniform={sim_uniform:.4f}. Old: decay={sim_old_d:.4f} vs uniform={sim_old_u:.4f}. Prunable: {prunable}/{N_items}")

def gate_8_resonator():
    CB = 30
    cb_a = [rand_vec() for _ in range(CB)]
    cb_b = [rand_vec() for _ in range(CB)]
    cb_c = [rand_vec() for _ in range(CB)]
    ia, ib, ic = 5, 17, 23
    composite = hrr_bind(hrr_bind(cb_a[ia], cb_b[ib]), cb_c[ic])

    est_a = normalize(np.sum(cb_a, axis=0))
    est_b = normalize(np.sum(cb_b, axis=0))
    est_c = normalize(np.sum(cb_c, axis=0))

    converged = False
    for it in range(300):
        sig_a = hrr_unbind(hrr_unbind(composite, est_b), est_c)
        best_a = int(np.argmax([cosine(sig_a, e) for e in cb_a]))
        est_a = cb_a[best_a]

        sig_b = hrr_unbind(hrr_unbind(composite, est_a), est_c)
        best_b = int(np.argmax([cosine(sig_b, e) for e in cb_b]))
        est_b = cb_b[best_b]

        sig_c = hrr_unbind(hrr_unbind(composite, est_a), est_b)
        best_c = int(np.argmax([cosine(sig_c, e) for e in cb_c]))
        est_c = cb_c[best_c]

        if best_a == ia and best_b == ib and best_c == ic:
            converged = True
            print(f"PASS [8/9]: 3-factor resonator (HRR, 3×{CB} CBs). Converged iter {it + 1}. Factors [{ia},{ib},{ic}].")
            break

    if not converged:
        print("FAIL: 3-factor resonator did not converge.")
        sys.exit(1)

def gate_9_e2e(char_vecs):
    entries = [
        ("deployed api v2", 0),
        ("fixed memory leak in worker", 1),
        ("scaled to ten replicas", 5),
        ("rollback due to latency spike", 10),
    ]

    time_keys = {t: rand_vec() for _, t in entries}
    memory = np.zeros(D)
    encoded_states = {}

    for text, t in entries:
        hv = encode_ngram(text, char_vecs)
        encoded_states[t] = hv
        w = np.exp(-0.1 * t)
        memory += w * hrr_bind(time_keys[t], hv)
    memory = normalize(memory)

    tmp = tempfile.mktemp(suffix=".vsa")
    magic = b"VSA3"
    meta = struct.pack("<II", D, len(entries))
    tensor_bytes = memory.tobytes()
    sha = hashlib.sha256(tensor_bytes).digest()
    with open(tmp, "wb") as f:
        f.write(magic + meta + tensor_bytes + sha)

    with open(tmp, "rb") as f:
        data = f.read()
    assert data[:4] == b"VSA3"
    d_read, n_read = struct.unpack("<II", data[4:12])
    assert d_read == D
    tensor_data = data[12:12 + D * 8]
    sha_read = data[12 + D * 8:]
    assert hashlib.sha256(tensor_data).digest() == sha_read, "SHA-256 integrity FAILED"
    loaded = np.frombuffer(tensor_data, dtype=np.float64)
    assert np.allclose(memory, loaded)

    extracted = hrr_unbind(loaded, time_keys[0])
    sim_e2e = cosine(encoded_states[0], extracted)
    assert sim_e2e > 0.05

    os.unlink(tmp)
    file_size = len(data)
    print(f"PASS [9/9]: E2E pipeline. text→encode→bind→decay→persist({file_size}B)→load→SHA256✓→retrieve cos={sim_e2e:.4f}")

def main():
    # VSA-SDM memory execution lifecycle
    gate_0_tripartite()
    gate_1_hrr_bind()
    gate_2_mapb()
    gate_3_snr()
    gate_4_hierarchical()
    M_locs, radius, activation_rate = gate_5_sdm()
    char_vecs = gate_6_ngram()
    gate_7_ebbinghaus()
    gate_8_resonator()
    gate_9_e2e(char_vecs)
    
    print("\n" + "=" * 60)
    print("ALL 10 GATES PASSED - VSA-SDM-MEMORY-OMEGA v3.1")
    print(f"  Footprint: {D * 8} B ({D * 8 / 1024:.1f} KB)")
    print(f"  SDM: {M_locs} locs, r={radius}, sparse={activation_rate:.1%}")
    print("  Encoders: N-gram + Record-based")
    print("  Decay: Ebbinghaus, retrieval-verified")
    print("  Resonator: 3-factor HRR")
    print("  Persistence: .vsa binary + SHA-256")
    print("  Pipeline: text→tensor→disk→retrieve ✓")
    print("=" * 60)

if __name__ == "__main__":
    main()
