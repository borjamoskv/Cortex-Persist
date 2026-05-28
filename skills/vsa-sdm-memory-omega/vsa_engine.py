"""
VSA-SDM Engine v3.1 — Sovereign Context Collapse Module
Importable Python module for Vector Symbolic Architecture operations.

Usage:
    from vsa_engine import VSAEngine

    engine = VSAEngine(D=10000, algebra="HRR")
    engine.encode_text("deployed api v2")
    engine.bind(time_key, state_vec)
    engine.retrieve(time_key)
    engine.save("memory.vsa")
    engine.load("memory.vsa")
"""
import hashlib
import struct
import time as _time
from pathlib import Path

import numpy as np


class VSAEngine:
    """Core VSA engine supporting HRR and MAP-B algebras."""

    MAGIC = b"VSA3"

    def __init__(self, D=10000, algebra="HRR", seed=None):
        """
        Args:
            D: Dimensionality of hypervectors.
            algebra: "HRR" (real-valued, FFT) or "MAPB" (bipolar, exact).
            seed: RNG seed for deterministic operation.
        """
        self.D = D
        self.algebra = algebra.upper()
        self.rng = np.random.default_rng(seed)
        self._codebook = {}
        self._char_vecs = None
        self._field_keys = {}
        self.memory = np.zeros(D)
        self._items = []  # (key_vec, state_vec, timestamp, weight)

    # ── Vector Generation ──

    def random_vec(self):
        """Generate a unit-norm random hypervector."""
        v = self.rng.standard_normal(self.D)
        return v / np.linalg.norm(v)

    def random_bipolar(self):
        """Generate a random bipolar {-1, +1}^D vector."""
        return self.rng.choice([-1.0, 1.0], size=self.D)

    def random_binary(self):
        """Generate a random binary {0, 1}^D vector."""
        return self.rng.integers(0, 2, size=self.D).astype(np.int8)

    # ── Core Algebra ──

    def bind(self, x, y):
        """Bind two vectors (association)."""
        if self.algebra == "MAPB":
            return x * y
        # HRR: circular convolution via FFT
        return np.fft.ifft(np.fft.fft(x) * np.fft.fft(y)).real

    def unbind(self, composite, key):
        """Unbind: extract value given key from composite."""
        if self.algebra == "MAPB":
            return composite * key  # self-inverse
        # HRR: circular correlation
        return np.fft.ifft(
            np.fft.fft(composite) * np.conj(np.fft.fft(key))
        ).real

    def bundle(self, vectors, weights=None):
        """Superimpose multiple vectors with optional weights."""
        if weights is None:
            weights = np.ones(len(vectors))
        result = np.zeros(self.D)
        for v, w in zip(vectors, weights):
            result += w * v
        return self.normalize(result)

    @staticmethod
    def normalize(v):
        n = np.linalg.norm(v)
        return v / n if n > 1e-12 else v

    @staticmethod
    def permute(v, k):
        """Cyclic shift by k positions (sequence encoding)."""
        return np.roll(v, k)

    @staticmethod
    def cosine(a, b):
        """Cosine similarity."""
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-12 or nb < 1e-12:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    # ── Text Encoding ──

    def _init_char_vecs(self):
        if self._char_vecs is None:
            alpha = "abcdefghijklmnopqrstuvwxyz0123456789 .,;:!?-_"
            self._char_vecs = {c: self.random_vec() for c in alpha}

    def encode_text(self, text, n=3):
        """Encode text via character n-gram with positional permutation."""
        self._init_char_vecs()
        text = text.lower()
        doc = np.zeros(self.D)
        ct = 0
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            if all(c in self._char_vecs for c in gram):
                gv = self._char_vecs[gram[0]]
                for k in range(1, n):
                    gv = self.bind(
                        self.permute(self._char_vecs[gram[k]], k), gv
                    )
                doc += gv
                ct += 1
        return self.normalize(doc) if ct > 0 else doc

    def encode_record(self, record):
        """Encode {key: value_text} structured data."""
        self._init_char_vecs()
        rec = np.zeros(self.D)
        for key, val in record.items():
            if key not in self._field_keys:
                self._field_keys[key] = self.random_vec()
            val_vec = self.encode_text(str(val))
            rec += self.bind(self._field_keys[key], val_vec)
        return self.normalize(rec)

    # ── Memory Operations ──

    def memorize(self, key_vec, state_vec, timestamp=None, decay_lambda=0.0):
        """Add a bound pair to the memory tensor with optional decay."""
        if timestamp is None:
            timestamp = _time.time()
        self._items.append((key_vec, state_vec, timestamp, decay_lambda))
        self._rebuild_memory()

    def _rebuild_memory(self):
        """Rebuild memory tensor with current decay weights."""
        now = _time.time()
        self.memory = np.zeros(self.D)
        for key, state, ts, lam in self._items:
            dt = now - ts
            w = np.exp(-lam * dt) if lam > 0 else 1.0
            self.memory += w * self.bind(key, state)
        self.memory = self.normalize(self.memory)

    def recall(self, key_vec):
        """Retrieve a state from the memory tensor."""
        return self.unbind(self.memory, key_vec)

    def forget(self, epsilon=0.01):
        """Purge items whose decay weight has fallen below epsilon."""
        now = _time.time()
        before = len(self._items)
        self._items = [
            (k, s, ts, lam) for k, s, ts, lam in self._items
            if lam == 0 or np.exp(-lam * (now - ts)) >= epsilon
        ]
        self._rebuild_memory()
        return before - len(self._items)

    @property
    def snr(self):
        """Current signal-to-noise ratio estimate."""
        n = len(self._items)
        return np.sqrt(self.D / n) if n > 0 else float('inf')

    @property
    def item_count(self):
        return len(self._items)

    # ── Codebook & SDM ──

    def register_codebook(self, name, vectors):
        """Register a named codebook for clean-up / resonator ops."""
        self._codebook[name] = list(vectors)

    def cleanup(self, noisy_vec, codebook_name):
        """Project noisy vector onto nearest codebook entry."""
        cb = self._codebook.get(codebook_name)
        if not cb:
            raise ValueError(f"No codebook: {codebook_name}")
        sims = [self.cosine(noisy_vec, e) for e in cb]
        best = int(np.argmax(sims))
        return cb[best], best, sims[best]

    def resonate(self, composite, codebook_names, max_iter=100):
        """
        Resonator network: factor a composite into components.
        Args:
            composite: The bound composite vector.
            codebook_names: List of codebook names, one per factor.
            max_iter: Maximum iterations.
        Returns:
            List of (codebook_entry, index) tuples, one per factor.
        """
        n_factors = len(codebook_names)
        cbs = [self._codebook[n] for n in codebook_names]
        # Initialize estimates as superposition
        estimates = [self.normalize(np.sum(cb, axis=0)) for cb in cbs]

        for it in range(max_iter):
            prev = [int(np.argmax([self.cosine(e, v) for v in cb]))
                    for e, cb in zip(estimates, cbs)]

            for f in range(n_factors):
                # Unbind all other estimates
                signal = composite.copy()
                for g in range(n_factors):
                    if g != f:
                        signal = self.unbind(signal, estimates[g])
                # Project onto codebook
                _, best, _ = self.cleanup(signal, codebook_names[f])
                estimates[f] = cbs[f][best]

            curr = [int(np.argmax([self.cosine(e, v) for v in cb]))
                    for e, cb in zip(estimates, cbs)]
            if curr == prev:
                return [(cbs[f][curr[f]], curr[f]) for f in range(n_factors)]

        return [(cbs[f][curr[f]], curr[f]) for f in range(n_factors)]

    # ── Persistence ──

    def save(self, path):
        """Serialize memory tensor to .vsa binary with SHA-256."""
        tensor_bytes = self.memory.tobytes()
        sha = hashlib.sha256(tensor_bytes).digest()
        n_items = len(self._items)
        with open(path, "wb") as f:
            f.write(self.MAGIC)
            f.write(struct.pack("<II", self.D, n_items))
            f.write(tensor_bytes)
            f.write(sha)
        return len(tensor_bytes) + 44  # magic + header + sha

    def load(self, path):
        """Load and verify a .vsa file."""
        with open(path, "rb") as f:
            data = f.read()
        if data[:4] != self.MAGIC:
            raise ValueError("Invalid .vsa file (bad magic)")
        d, n = struct.unpack("<II", data[4:12])
        if d != self.D:
            raise ValueError(f"Dimension mismatch: file={d}, engine={self.D}")
        tensor_data = data[12:12 + d * 8]
        sha_stored = data[12 + d * 8:12 + d * 8 + 32]
        sha_computed = hashlib.sha256(tensor_data).digest()
        if sha_computed != sha_stored:
            raise ValueError("SHA-256 integrity check FAILED")
        self.memory = np.frombuffer(tensor_data, dtype=np.float64).copy()
        return n

    # ── LLM Embedding Projection ──

    def project_from_llm(self, embedding, llm_dim):
        """
        Project an LLM embedding (dim=llm_dim) into VSA space (dim=D).
        Uses a deterministic random projection matrix (Johnson-Lindenstrauss).
        """
        # Deterministic projection: seeded by llm_dim for reproducibility
        proj_rng = np.random.default_rng(seed=llm_dim)
        # Sparse random projection (sqrt(3)-sparse Achlioptas)
        # P[i,j] ∈ {-1, 0, +1} with probs {1/6, 2/3, 1/6}
        proj = proj_rng.choice(
            [-1.0, 0.0, 0.0, 0.0, 1.0],  # approx 1/5, 3/5, 1/5
            size=(self.D, llm_dim)
        )
        projected = proj @ embedding
        return self.normalize(projected)

    def project_to_llm(self, vsa_vec, llm_dim):
        """
        Project VSA vector back to LLM embedding space.
        Pseudo-inverse via transpose of the same projection matrix.
        """
        proj_rng = np.random.default_rng(seed=llm_dim)
        proj = proj_rng.choice(
            [-1.0, 0.0, 0.0, 0.0, 1.0],
            size=(self.D, llm_dim)
        )
        # Pseudo-inverse projection (P^T @ vsa_vec)
        return self.normalize(proj.T @ vsa_vec)

    # ── Diagnostics ──

    def capacity_report(self):
        """Return capacity diagnostics."""
        n = self.item_count
        snr = self.snr
        chunk_threshold = int(np.sqrt(self.D))
        needs_chunking = n > chunk_threshold
        return {
            "dimensions": self.D,
            "items": n,
            "snr": round(snr, 2),
            "chunk_threshold": chunk_threshold,
            "needs_chunking": needs_chunking,
            "memory_bytes": self.D * 8,
            "algebra": self.algebra,
        }
