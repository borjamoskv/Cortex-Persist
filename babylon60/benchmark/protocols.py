# [C5-REAL] Exergy-Maximized
"""Behavioral Latent Space Protocols — Black-Box LLM Instrumentation Layer.

Implements the operational stack for system identification of LLMs as discrete-time
nonlinear dynamical systems. This is NOT a model fingerprinter — it is a behavioral
drift detector, consistency verifier, and trajectory comparator.

Mathematical Foundation:
    State transition:  ŝ(t) = h(prompt, response, history, seed_proxy)
    Feature vector:    x_t = [f_1, f_2, ..., f_n]  (measurable signals, not opinions)
    Trajectory:        T = [x_1, x_2, ..., x_K]
    Drift metric:      JSD(P_new || P_old) ∈ [0, 1] bits

Stack:
    SQLite for events/metrics, embeddings for semantic distance,
    DTW + Mahalanobis for trajectory comparison, JSD/Wasserstein for drift.

Author: Borja Moskv (borjamoskv)
License: Apache-2.0
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto

__all__ = [
    "ExcitationFamily",
    "Probe",
    "ProbeBank",
    "ResponseFeatures",
    "StateEstimator",
    "BehavioralCoverage",
    "TrajectoryComparator",
    "DriftDetector",
    "AlarmPolicy",
    "AlarmVerdict",
    "SessionRunner",
]

logger = logging.getLogger("cortex.benchmark.protocols")

# ---------------------------------------------------------------------------
# §A — Excitation Families & Probe Bank
# ---------------------------------------------------------------------------


class ExcitationFamily(Enum):
    """Five orthogonal signal families for exciting all dynamic modes."""

    LOGIC = auto()         # Inductive/deductive abstraction → generalization capacity
    NARRATIVE = auto()     # Text mutation & compression → processing/compression
    MEMORY = auto()        # Key-value injection with distractors → contextual retention
    ADVERSARIAL = auto()   # Contradictions, traps, red herrings → perturbation robustness
    METACOGNITIVE = auto() # Forced self-evaluation & negative feedback → self-correction


# Minimum probe counts per family (§A of the operative framework)
FAMILY_PROBE_COUNTS: dict[ExcitationFamily, int] = {
    ExcitationFamily.LOGIC: 30,
    ExcitationFamily.NARRATIVE: 30,
    ExcitationFamily.MEMORY: 20,
    ExcitationFamily.ADVERSARIAL: 30,
    ExcitationFamily.METACOGNITIVE: 20,
}


@dataclass(frozen=True, slots=True)
class Probe:
    """Single excitation stimulus with ground truth and scoring criteria.

    Attributes:
        probe_id: Deterministic identifier (sha256 of family + prompt).
        family: Excitation family this probe belongs to.
        prompt: The stimulus text sent to the model.
        ground_truth: Expected structural invariant (None for open probes).
        constraints: Machine-verifiable constraints on the response.
        version: Probe version for baseline stability tracking.
    """

    probe_id: str
    family: ExcitationFamily
    prompt: str
    ground_truth: str | None = None
    constraints: dict[str, str | float] = field(default_factory=dict)
    version: int = 1

    @staticmethod
    def make_id(family: ExcitationFamily, prompt: str) -> str:
        payload = f"{family.name}:{prompt}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class ProbeBank:
    """Registry of probes organized by excitation family.

    Enforces minimum cardinality per family.
    """

    def __init__(self) -> None:
        self._probes: dict[ExcitationFamily, list[Probe]] = {
            f: [] for f in ExcitationFamily
        }

    def register(self, probe: Probe) -> None:
        self._probes[probe.family].append(probe)

    def register_batch(self, probes: Sequence[Probe]) -> None:
        for p in probes:
            self.register(p)

    def get_family(self, family: ExcitationFamily) -> list[Probe]:
        return list(self._probes[family])

    def all_probes(self) -> list[Probe]:
        result: list[Probe] = []
        for family_probes in self._probes.values():
            result.extend(family_probes)
        return result

    def validate_cardinality(self) -> dict[ExcitationFamily, tuple[int, int, bool]]:
        """Returns (actual, required, passes) per family."""
        return {
            f: (len(self._probes[f]), FAMILY_PROBE_COUNTS[f],
                len(self._probes[f]) >= FAMILY_PROBE_COUNTS[f])
            for f in ExcitationFamily
        }

    @property
    def total(self) -> int:
        return sum(len(v) for v in self._probes.values())


# ---------------------------------------------------------------------------
# §B — Feature Extractor (Measurable signals, not opinions)
# ---------------------------------------------------------------------------

_HEDGE_PATTERNS = re.compile(
    r"\b(perhaps|maybe|might|could be|i think|it seems|possibly|arguably"
    r"|probably|in my opinion|i believe|it appears|not sure|uncertain"
    r"|quizás|tal vez|podría|creo que|parece que|posiblemente)\b",
    re.IGNORECASE,
)

_NEGATION_PATTERNS = re.compile(
    r"\b(i cannot|i can't|i'm unable|i don't|i won't|i shouldn't"
    r"|no puedo|no debo|no es posible|no tengo|fuera de mi alcance)\b",
    re.IGNORECASE,
)

_SELF_CORRECTION = re.compile(
    r"\b(actually|wait|correction|let me reconsider|i was wrong"
    r"|en realidad|corrijo|me equivoqué|rectifico|pensándolo bien)\b",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"[a-záéíóúñü]{2,}", re.IGNORECASE)


@dataclass(slots=True)
class ResponseFeatures:
    """Measurable feature vector extracted from a single model response.

    Every field is a computable signal — zero subjectivity.

    Feature dimensions (n=12):
        f1:  response_length_chars
        f2:  response_length_tokens (whitespace split)
        f3:  lexical_entropy (Shannon H over token frequencies)
        f4:  type_token_ratio (unique/total tokens)
        f5:  hedge_rate (hedging phrases per 100 tokens)
        f6:  negation_rate (refusal/evasion per 100 tokens)
        f7:  self_correction_count
        f8:  sentence_count
        f9:  avg_sentence_length
        f10: code_block_count
        f11: numeric_density (numbers per 100 tokens)
        f12: latency_ms (wall-clock TTFT or full response)
    """

    response_length_chars: int = 0
    response_length_tokens: int = 0
    lexical_entropy: float = 0.0
    type_token_ratio: float = 0.0
    hedge_rate: float = 0.0
    negation_rate: float = 0.0
    self_correction_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    code_block_count: int = 0
    numeric_density: float = 0.0
    latency_ms: float = 0.0

    def to_vector(self) -> list[float]:
        """Returns the 12-dimensional feature vector as a flat list."""
        return [
            float(self.response_length_chars),
            float(self.response_length_tokens),
            self.lexical_entropy,
            self.type_token_ratio,
            self.hedge_rate,
            self.negation_rate,
            float(self.self_correction_count),
            float(self.sentence_count),
            self.avg_sentence_length,
            float(self.code_block_count),
            self.numeric_density,
            self.latency_ms,
        ]

    @staticmethod
    def dimension() -> int:
        return 12


def extract_features(response: str, latency_ms: float = 0.0) -> ResponseFeatures:
    """Extract measurable features from a raw model response.

    This is the state estimator: ŝ(t) = h(prompt, response, history, seed_proxy).
    The prompt and history context are encoded via the response they produced.
    """
    tokens = response.split()
    n_tokens = len(tokens) or 1

    # Lexical entropy (Shannon H over word frequencies)
    word_tokens = _TOKEN_RE.findall(response.lower())
    word_count = len(word_tokens) or 1
    counts = Counter(word_tokens)
    unique_count = len(counts)
    entropy = 0.0
    for c in counts.values():
        p = c / word_count
        if p > 0:
            entropy -= p * math.log2(p)

    # Type-token ratio
    ttr = unique_count / word_count if word_count > 0 else 0.0

    # Hedging
    hedge_matches = len(_HEDGE_PATTERNS.findall(response))
    hedge_rate = (hedge_matches / n_tokens) * 100

    # Negation / evasion
    neg_matches = len(_NEGATION_PATTERNS.findall(response))
    neg_rate = (neg_matches / n_tokens) * 100

    # Self-correction
    self_corr = len(_SELF_CORRECTION.findall(response))

    # Sentence segmentation (heuristic: split on .!? followed by space/newline)
    sentences = re.split(r"[.!?]+[\s\n]+", response.strip())
    sentences = [s for s in sentences if s.strip()]
    n_sentences = len(sentences) or 1
    avg_sent_len = len(response) / n_sentences

    # Code blocks
    code_blocks = response.count("```")

    # Numeric density
    nums = re.findall(r"\d+\.?\d*", response)
    numeric_density = (len(nums) / n_tokens) * 100

    return ResponseFeatures(
        response_length_chars=len(response),
        response_length_tokens=n_tokens,
        lexical_entropy=round(entropy, 4),
        type_token_ratio=round(ttr, 4),
        hedge_rate=round(hedge_rate, 4),
        negation_rate=round(neg_rate, 4),
        self_correction_count=self_corr,
        sentence_count=n_sentences,
        avg_sentence_length=round(avg_sent_len, 2),
        code_block_count=code_blocks // 2,  # pairs
        numeric_density=round(numeric_density, 4),
        latency_ms=round(latency_ms, 2),
    )


# ---------------------------------------------------------------------------
# §B.1 — State Estimator (separates inferred state from raw text)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class EstimatedState:
    """Inferred behavioral state at turn t.

    This is ŝ(t) = h(prompt, response, history, seed_proxy).
    NOT the model's internal state — it's our observable approximation.
    """

    turn: int
    probe_id: str
    family: ExcitationFamily
    features: ResponseFeatures
    seed: int | None = None
    timestamp: float = field(default_factory=time.time)

    def feature_vector(self) -> list[float]:
        return self.features.to_vector()


class StateEstimator:
    """Accumulates EstimatedStates across a conversation/session.

    Provides the trajectory T = [ŝ(1), ŝ(2), ..., ŝ(K)] for DTW comparison.
    """

    def __init__(self, model_id: str, session_id: str) -> None:
        self.model_id = model_id
        self.session_id = session_id
        self.states: list[EstimatedState] = []

    def observe(
        self,
        probe: Probe,
        response: str,
        latency_ms: float = 0.0,
        seed: int | None = None,
    ) -> EstimatedState:
        """Process a (probe, response) pair into an EstimatedState."""
        features = extract_features(response, latency_ms)
        state = EstimatedState(
            turn=len(self.states),
            probe_id=probe.probe_id,
            family=probe.family,
            features=features,
            seed=seed,
        )
        self.states.append(state)
        return state

    def trajectory(self) -> list[list[float]]:
        """Returns the feature matrix: K × D where K=turns, D=feature_dim."""
        return [s.feature_vector() for s in self.states]

    def trajectory_by_family(
        self, family: ExcitationFamily
    ) -> list[list[float]]:
        return [
            s.feature_vector()
            for s in self.states
            if s.family == family
        ]


# ---------------------------------------------------------------------------
# §C — Behavioral Coverage Entropy (H_cov)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Result of behavioral coverage analysis.

    Attributes:
        h_cov: Behavioral Coverage Entropy in bits.
        h_max: Maximum possible entropy (log₂ D).
        variance_ratios: PCA explained variance ratios per dimension.
        coverage_ratio: h_cov / h_max ∈ [0, 1]. 1.0 = uniform coverage.
        blind_dimensions: Dimensions with < 5% variance contribution.
    """

    h_cov: float
    h_max: float
    variance_ratios: list[float]
    coverage_ratio: float
    blind_dimensions: list[int]


class BehavioralCoverage:
    """Computes H_cov over a feature matrix from probe responses.

    H_cov(U) = -Σ p_d log₂ p_d

    Where p_d = Var(feature_d) / Σ Var(feature_k) — anchored to PCA
    explained variance ratios (not abstract "proportions").
    """

    @staticmethod
    def compute(feature_matrix: list[list[float]]) -> CoverageReport:
        """Compute behavioral coverage entropy from a K×D feature matrix.

        Args:
            feature_matrix: List of K feature vectors, each of dimension D.

        Returns:
            CoverageReport with H_cov, variance ratios, and blind spots.
        """
        if not feature_matrix or not feature_matrix[0]:
            return CoverageReport(
                h_cov=0.0, h_max=0.0, variance_ratios=[],
                coverage_ratio=0.0, blind_dimensions=[],
            )

        k = len(feature_matrix)
        d = len(feature_matrix[0])

        # Compute variance per dimension (column-wise)
        means = [0.0] * d
        for row in feature_matrix:
            for j in range(d):
                means[j] += row[j]
        means = [m / k for m in means]

        variances = [0.0] * d
        for row in feature_matrix:
            for j in range(d):
                variances[j] += (row[j] - means[j]) ** 2
        variances = [v / max(k - 1, 1) for v in variances]

        total_var = sum(variances)
        if total_var < 1e-15:
            return CoverageReport(
                h_cov=0.0, h_max=math.log2(d) if d > 1 else 0.0,
                variance_ratios=[0.0] * d,
                coverage_ratio=0.0, blind_dimensions=list(range(d)),
            )

        # p_d = Var(feature_d) / Σ Var(feature_k) — normalized variance ratios
        p = [v / total_var for v in variances]

        # H_cov = -Σ p_d log₂ p_d
        h_cov = 0.0
        for p_d in p:
            if p_d > 1e-15:
                h_cov -= p_d * math.log2(p_d)

        h_max = math.log2(d) if d > 1 else 0.0
        coverage_ratio = h_cov / h_max if h_max > 0 else 0.0

        blind = [i for i, p_d in enumerate(p) if p_d < 0.05]

        return CoverageReport(
            h_cov=round(h_cov, 4),
            h_max=round(h_max, 4),
            variance_ratios=[round(v, 6) for v in p],
            coverage_ratio=round(coverage_ratio, 4),
            blind_dimensions=blind,
        )


# ---------------------------------------------------------------------------
# §D — Trajectory Comparator (DTW + Mahalanobis)
# ---------------------------------------------------------------------------


class TrajectoryComparator:
    """Compares conversational trajectories via Dynamic Time Warping.

    Distance metric: Mahalanobis (accounts for covariance structure).
    Default: pooled covariance from both trajectories.

    DTW(T_A, T_B) = min_π Σ_{(i,j)∈π} d(ŝ_A(i), ŝ_B(j))
    """

    @staticmethod
    def _euclidean(a: list[float], b: list[float]) -> float:
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b, strict=False)))

    @staticmethod
    def _mahalanobis(
        a: list[float],
        b: list[float],
        inv_cov: list[list[float]],
    ) -> float:
        """Mahalanobis distance: sqrt((a-b)^T Σ^{-1} (a-b))."""
        d = len(a)
        diff = [ai - bi for ai, bi in zip(a, b, strict=False)]
        result = 0.0
        for i in range(d):
            for j in range(d):
                result += diff[i] * inv_cov[i][j] * diff[j]
        return math.sqrt(max(result, 0.0))

    @staticmethod
    def _compute_pooled_inv_cov(
        t_a: list[list[float]], t_b: list[list[float]]
    ) -> list[list[float]]:
        """Compute inverse of pooled covariance matrix.

        Falls back to diagonal (independent dimensions) if matrix is singular.
        """
        combined = t_a + t_b
        n = len(combined)
        d = len(combined[0]) if combined else 0
        if n < 2 or d == 0:
            return [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]

        # Mean
        mu = [0.0] * d
        for row in combined:
            for j in range(d):
                mu[j] += row[j]
        mu = [m / n for m in mu]

        # Covariance matrix
        cov = [[0.0] * d for _ in range(d)]
        for row in combined:
            for i in range(d):
                for j in range(d):
                    cov[i][j] += (row[i] - mu[i]) * (row[j] - mu[j])
        for i in range(d):
            for j in range(d):
                cov[i][j] /= max(n - 1, 1)

        # Regularize diagonal to prevent singularity
        for i in range(d):
            cov[i][i] += 1e-6

        # Invert via Gauss-Jordan (pure Python, no numpy dependency)
        aug = [cov[i][:] + [1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]
        for col in range(d):
            # Partial pivoting
            max_row = max(range(col, d), key=lambda r: abs(aug[r][col]))
            aug[col], aug[max_row] = aug[max_row], aug[col]
            pivot = aug[col][col]
            if abs(pivot) < 1e-12:
                # Singular — fall back to identity
                return [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]
            for j in range(2 * d):
                aug[col][j] /= pivot
            for row in range(d):
                if row != col:
                    factor = aug[row][col]
                    for j in range(2 * d):
                        aug[row][j] -= factor * aug[col][j]

        inv = [aug[i][d:] for i in range(d)]
        return inv

    @staticmethod
    def dtw(
        t_a: list[list[float]],
        t_b: list[list[float]],
        use_mahalanobis: bool = True,
    ) -> float:
        """Compute DTW distance between two trajectories.

        Args:
            t_a: Trajectory A — list of feature vectors.
            t_b: Trajectory B — list of feature vectors.
            use_mahalanobis: If True, use Mahalanobis distance. Else Euclidean.

        Returns:
            DTW distance (lower = more similar trajectories).
        """
        n = len(t_a)
        m = len(t_b)
        if n == 0 or m == 0:
            return float("inf")

        if use_mahalanobis:
            inv_cov = TrajectoryComparator._compute_pooled_inv_cov(t_a, t_b)
            def dist_fn(a, b):
                return TrajectoryComparator._mahalanobis(a, b, inv_cov)
        else:
            dist_fn = TrajectoryComparator._euclidean

        # Standard DTW with O(nm) DP
        dtw_matrix = [[float("inf")] * (m + 1) for _ in range(n + 1)]
        dtw_matrix[0][0] = 0.0

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = dist_fn(t_a[i - 1], t_b[j - 1])
                dtw_matrix[i][j] = cost + min(
                    dtw_matrix[i - 1][j],      # insertion
                    dtw_matrix[i][j - 1],      # deletion
                    dtw_matrix[i - 1][j - 1],  # match
                )

        return dtw_matrix[n][m]

    @staticmethod
    def normalized_dtw(
        t_a: list[list[float]],
        t_b: list[list[float]],
        use_mahalanobis: bool = True,
    ) -> float:
        """DTW normalized by path length (comparable across trajectory sizes)."""
        raw = TrajectoryComparator.dtw(t_a, t_b, use_mahalanobis)
        path_len = len(t_a) + len(t_b)
        return raw / path_len if path_len > 0 else 0.0


# ---------------------------------------------------------------------------
# §E — Drift Detection (JSD / Wasserstein)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DriftReport:
    """Result of behavioral drift detection between two model versions.

    Attributes:
        jsd: Jensen-Shannon Divergence ∈ [0, 1] bits (symmetric, bounded).
        wasserstein_approx: Wasserstein-1 approximation (per-dimension, averaged).
        dimension_drifts: Per-dimension absolute mean shift (normalized).
        drift_detected: True if JSD exceeds threshold.
        alarm_dimensions: Dimensions with significant drift.
    """

    jsd: float
    wasserstein_approx: float
    dimension_drifts: list[float]
    drift_detected: bool
    alarm_dimensions: list[int]


class DriftDetector:
    """Detects behavioral drift between model versions using JSD and Wasserstein-1.

    JSD(P || Q) = ½ KL(P || M) + ½ KL(Q || M),  M = ½(P + Q)
    Symmetric, bounded ∈ [0, 1] bits. Superior to raw KL for production.
    """

    def __init__(self, jsd_threshold: float = 0.15, dim_threshold: float = 0.3) -> None:
        self.jsd_threshold = jsd_threshold
        self.dim_threshold = dim_threshold

    @staticmethod
    def _histogram(values: list[float], n_bins: int = 20) -> list[float]:
        """Create a normalized histogram (probability distribution)."""
        if not values:
            return [1.0 / n_bins] * n_bins
        v_min = min(values)
        v_max = max(values)
        spread = v_max - v_min
        if spread < 1e-15:
            hist = [0.0] * n_bins
            hist[0] = 1.0
            return hist

        bin_width = spread / n_bins
        hist = [0.0] * n_bins
        for v in values:
            idx = int((v - v_min) / bin_width)
            idx = min(idx, n_bins - 1)
            hist[idx] += 1

        total = sum(hist)
        return [h / total for h in hist] if total > 0 else [1.0 / n_bins] * n_bins

    @staticmethod
    def _kl_divergence(p: list[float], q: list[float]) -> float:
        """KL(P || Q) with Laplace smoothing to avoid log(0)."""
        eps = 1e-10
        return sum(
            pi * math.log2((pi + eps) / (qi + eps))
            for pi, qi in zip(p, q, strict=False)
            if pi > eps
        )

    @staticmethod
    def _jsd(p: list[float], q: list[float]) -> float:
        """Jensen-Shannon Divergence: symmetric, bounded ∈ [0, 1]."""
        m = [(pi + qi) / 2.0 for pi, qi in zip(p, q, strict=False)]
        return 0.5 * DriftDetector._kl_divergence(p, m) + \
               0.5 * DriftDetector._kl_divergence(q, m)

    @staticmethod
    def _wasserstein_1d(a: list[float], b: list[float]) -> float:
        """Wasserstein-1 (Earth Mover's Distance) for 1D sorted samples."""
        if not a or not b:
            return 0.0
        sa = sorted(a)
        sb = sorted(b)
        # Resample to same length via linear interpolation
        n = max(len(sa), len(sb))

        def interp(arr: list[float], size: int) -> list[float]:
            if len(arr) == size:
                return arr
            result = []
            for i in range(size):
                idx = i * (len(arr) - 1) / max(size - 1, 1)
                lo = int(idx)
                hi = min(lo + 1, len(arr) - 1)
                frac = idx - lo
                result.append(arr[lo] * (1 - frac) + arr[hi] * frac)
            return result

        ra = interp(sa, n)
        rb = interp(sb, n)
        return sum(abs(ai - bi) for ai, bi in zip(ra, rb, strict=False)) / n

    def detect(
        self,
        baseline_features: list[list[float]],
        current_features: list[list[float]],
        n_bins: int = 20,
    ) -> DriftReport:
        """Compare feature distributions between baseline and current.

        Args:
            baseline_features: K₁ × D feature matrix from baseline model/version.
            current_features: K₂ × D feature matrix from current model/version.
            n_bins: Histogram bins for JSD computation.

        Returns:
            DriftReport with JSD, Wasserstein, per-dimension drift, and alarms.
        """
        if not baseline_features or not current_features:
            return DriftReport(
                jsd=0.0, wasserstein_approx=0.0,
                dimension_drifts=[], drift_detected=False,
                alarm_dimensions=[],
            )

        d = len(baseline_features[0])
        jsd_per_dim: list[float] = []
        w1_per_dim: list[float] = []
        dim_drifts: list[float] = []
        alarm_dims: list[int] = []

        for dim in range(d):
            col_base = [row[dim] for row in baseline_features]
            col_curr = [row[dim] for row in current_features]

            # JSD per dimension
            hist_base = self._histogram(col_base, n_bins)
            hist_curr = self._histogram(col_curr, n_bins)
            jsd_dim = self._jsd(hist_base, hist_curr)
            jsd_per_dim.append(jsd_dim)

            # Wasserstein-1 per dimension
            w1 = self._wasserstein_1d(col_base, col_curr)
            w1_per_dim.append(w1)

            # Normalized mean shift
            mean_base = sum(col_base) / len(col_base)
            mean_curr = sum(col_curr) / len(col_curr)
            std_base = math.sqrt(
                sum((x - mean_base) ** 2 for x in col_base) / max(len(col_base) - 1, 1)
            )
            shift = abs(mean_curr - mean_base) / max(std_base, 1e-10)
            dim_drifts.append(round(shift, 4))

            if shift > self.dim_threshold:
                alarm_dims.append(dim)

        # Aggregate JSD (mean across dimensions)
        avg_jsd = sum(jsd_per_dim) / d if d > 0 else 0.0
        avg_w1 = sum(w1_per_dim) / d if d > 0 else 0.0

        return DriftReport(
            jsd=round(avg_jsd, 6),
            wasserstein_approx=round(avg_w1, 4),
            dimension_drifts=dim_drifts,
            drift_detected=avg_jsd > self.jsd_threshold,
            alarm_dimensions=alarm_dims,
        )


# ---------------------------------------------------------------------------
# §F — Alarm Policy Engine
# ---------------------------------------------------------------------------


class AlarmVerdict(Enum):
    """Operational verdict from the alarm policy."""

    NOMINAL = auto()       # All metrics within bounds
    WATCH = auto()         # Minor anomalies, increase monitoring frequency
    ALERT = auto()         # Significant drift, flag for review
    ABORT = auto()         # Critical drift, halt automated reliance on endpoint


@dataclass(frozen=True, slots=True)
class AlarmResult:
    """Full alarm evaluation result.

    Attributes:
        verdict: Operational verdict.
        reasons: List of triggered alarm conditions.
        coverage: CoverageReport for the current probe set.
        drift: DriftReport if baseline was available.
        seed_stability: Variance across seeds (lower = more deterministic).
    """

    verdict: AlarmVerdict
    reasons: list[str]
    coverage: CoverageReport | None = None
    drift: DriftReport | None = None
    seed_stability: float | None = None


class AlarmPolicy:
    """Decision engine for abort/lock/regenerate/continue.

    Thresholds are structurally motivated, not arbitrary:
      - JSD > 0.15 → behavioral signature has shifted enough to affect downstream
      - H_cov < 0.5 → benchmark is blind to >50% of behavioral dimensions
      - seed_variance > 0.3 → stochastic noise dominates signal
    """

    def __init__(
        self,
        jsd_watch: float = 0.08,
        jsd_alert: float = 0.15,
        jsd_abort: float = 0.30,
        coverage_min: float = 0.5,
        seed_var_max: float = 0.3,
    ) -> None:
        self.jsd_watch = jsd_watch
        self.jsd_alert = jsd_alert
        self.jsd_abort = jsd_abort
        self.coverage_min = coverage_min
        self.seed_var_max = seed_var_max

    def evaluate(
        self,
        coverage: CoverageReport | None = None,
        drift: DriftReport | None = None,
        seed_stability: float | None = None,
    ) -> AlarmResult:
        reasons: list[str] = []
        verdict = AlarmVerdict.NOMINAL

        # Coverage check
        if coverage and coverage.coverage_ratio < self.coverage_min:
            reasons.append(
                f"LOW_COVERAGE: H_cov/H_max = {coverage.coverage_ratio:.2f} "
                f"< {self.coverage_min}. Blind dims: {coverage.blind_dimensions}"
            )
            verdict = max(verdict, AlarmVerdict.WATCH, key=lambda v: v.value)

        # Drift check (escalating thresholds)
        if drift:
            if drift.jsd >= self.jsd_abort:
                reasons.append(
                    f"ABORT_DRIFT: JSD = {drift.jsd:.4f} >= {self.jsd_abort}. "
                    f"Alarm dims: {drift.alarm_dimensions}"
                )
                verdict = AlarmVerdict.ABORT
            elif drift.jsd >= self.jsd_alert:
                reasons.append(
                    f"ALERT_DRIFT: JSD = {drift.jsd:.4f} >= {self.jsd_alert}. "
                    f"Alarm dims: {drift.alarm_dimensions}"
                )
                verdict = max(verdict, AlarmVerdict.ALERT, key=lambda v: v.value)
            elif drift.jsd >= self.jsd_watch:
                reasons.append(
                    f"WATCH_DRIFT: JSD = {drift.jsd:.4f} >= {self.jsd_watch}."
                )
                verdict = max(verdict, AlarmVerdict.WATCH, key=lambda v: v.value)

        # Seed stability check (replication control)
        if seed_stability is not None and seed_stability > self.seed_var_max:
            reasons.append(
                f"SEED_NOISE: variance = {seed_stability:.4f} > {self.seed_var_max}. "
                "Stochastic noise dominates signal — increase seed count."
            )
            verdict = max(verdict, AlarmVerdict.ALERT, key=lambda v: v.value)

        if not reasons:
            reasons.append("All metrics within operational bounds.")

        return AlarmResult(
            verdict=verdict,
            reasons=reasons,
            coverage=coverage,
            drift=drift,
            seed_stability=seed_stability,
        )


# ---------------------------------------------------------------------------
# §G — Session Runner (Orchestration)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProbeResult:
    """Single probe execution result."""

    probe: Probe
    response: str
    features: ResponseFeatures
    seed: int | None
    latency_ms: float
    timestamp: float = field(default_factory=time.time)


class SessionRunner:
    """Orchestrates a complete evaluation session.

    Coordinates: ProbeBank → Feature Extraction → Coverage → Drift → Alarm.

    Usage:
        runner = SessionRunner(probe_bank, model_id="gpt-4o-2026-06")
        # For each probe, call runner.record(probe, response, latency_ms, seed)
        coverage = runner.compute_coverage()
        drift = runner.compute_drift(baseline_features)
        verdict = runner.evaluate(baseline_features)
    """

    def __init__(self, probe_bank: ProbeBank, model_id: str) -> None:
        self.probe_bank = probe_bank
        self.model_id = model_id
        self.estimator = StateEstimator(model_id, session_id=f"{model_id}_{int(time.time())}")
        self.results: list[ProbeResult] = []

    def record(
        self,
        probe: Probe,
        response: str,
        latency_ms: float = 0.0,
        seed: int | None = None,
    ) -> ProbeResult:
        """Record a single (probe, response) observation."""
        state = self.estimator.observe(probe, response, latency_ms, seed)
        result = ProbeResult(
            probe=probe,
            response=response,
            features=state.features,
            seed=seed,
            latency_ms=latency_ms,
        )
        self.results.append(result)
        return result

    def feature_matrix(self) -> list[list[float]]:
        return self.estimator.trajectory()

    def feature_matrix_by_family(self, family: ExcitationFamily) -> list[list[float]]:
        return self.estimator.trajectory_by_family(family)

    def compute_coverage(self) -> CoverageReport:
        return BehavioralCoverage.compute(self.feature_matrix())

    def compute_drift(self, baseline_features: list[list[float]]) -> DriftReport:
        detector = DriftDetector()
        return detector.detect(baseline_features, self.feature_matrix())

    def compute_seed_stability(self) -> float:
        """Variance across seeds for the same probes.

        Groups results by probe_id, computes per-group feature variance,
        then averages across groups and dimensions.
        """
        from collections import defaultdict
        groups: dict[str, list[list[float]]] = defaultdict(list)
        for r in self.results:
            groups[r.probe.probe_id].append(r.features.to_vector())

        # Only consider probes with multiple seeds
        multi_seed = {k: v for k, v in groups.items() if len(v) > 1}
        if not multi_seed:
            return 0.0

        d = ResponseFeatures.dimension()
        total_var = 0.0
        count = 0
        for vectors in multi_seed.values():
            k = len(vectors)
            for dim in range(d):
                col = [v[dim] for v in vectors]
                mu = sum(col) / k
                var = sum((x - mu) ** 2 for x in col) / max(k - 1, 1)
                # Normalize by mean to make variance comparable across dimensions
                norm = abs(mu) if abs(mu) > 1e-10 else 1.0
                total_var += var / (norm ** 2)
                count += 1

        return total_var / count if count > 0 else 0.0

    def evaluate(
        self,
        baseline_features: list[list[float]] | None = None,
        policy: AlarmPolicy | None = None,
    ) -> AlarmResult:
        """Full evaluation: coverage + drift + seed stability → alarm verdict."""
        if policy is None:
            policy = AlarmPolicy()

        coverage = self.compute_coverage()
        drift = self.compute_drift(baseline_features) if baseline_features else None
        seed_var = self.compute_seed_stability()

        return policy.evaluate(
            coverage=coverage,
            drift=drift,
            seed_stability=seed_var if seed_var > 0 else None,
        )

    def summary(self) -> dict[str, object]:
        """Structured session summary for ledger emission."""
        return {
            "model_id": self.model_id,
            "session_id": self.estimator.session_id,
            "total_probes": len(self.results),
            "families_covered": list({
                r.probe.family.name for r in self.results
            }),
            "timestamp": time.time(),
        }
