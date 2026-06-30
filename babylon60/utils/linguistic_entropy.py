from decimal import Decimal
# [C5-REAL] Exergy-Maximized | borjamoskv
"""
Linguistic Entropy Detector (Ω₁₇) — PLAYGROUND EDITION
============================================================
Full-spectrum linguistic entropy analysis:
  - Shannon entropy (char, word, bigram, trigram)
  - Burstiness coefficient (Goh-Barabási)
  - Sentence complexity (avg length, variance)
  - Context rot (window-based entropy decay)
  - Green theater / LLM slop density (Ω₁₃)
  - Lexical diversity (TTR, MATTR)
  - Exergy score [0.0, 1.0]
"""

import math
import re
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

# ─── Slop patterns corpus ────────────────────────────────────────────────────

_SLOP_PATTERNS: list[tuple[str, float]] = [
    # (regex, severity_weight)
    (r"Aquí tienes el código", 1.0),
    (r"Espero que esto ayude", 1.0),
    (r"Por supuesto[,.]?", 0.8),
    (r"Entendido[,.]?", 0.6),
    (r"Como modelo de lenguaje", 1.0),
    (r"Here is the code", 1.0),
    (r"I hope this helps", 1.0),
    (r"Of course[,.]?", 0.8),
    (r"Understood[,.]?", 0.6),
    (r"As an AI language model", 1.0),
    (r"Claro[,.]?\s+aquí tienes", 0.9),
    (r"No dudes en preguntar", 0.9),
    (r"Feel free to ask", 0.9),
    (r"Es importante (tener en cuenta|notar|recordar)", 0.8),
    (r"It('s| is) important to (note|remember)", 0.8),
    (r"Cabe destacar que", 0.7),
    (r"¡(Claro|Por supuesto|Excelente)!", 0.8),
    (r"Great[,!]?\s+(let('s| us)|I('ll| will))", 0.7),
    (r"I'd be happy to", 0.9),
    (r"I('m| am) here to help", 0.9),
    (r"Certainly[,!]?", 0.7),
    (r"Absolutely[,!]?", 0.7),
    (r"Definitivamente[,!]?", 0.6),
    (r"Sin lugar a dudas[,!]?", 0.7),
    (r"A continuación[,:]", 0.5),
    (r"Below you('ll| will) find", 0.5),
    (r"Espero que.*útil", 0.9),
    (r"I hope.*helpful", 0.9),
]


def _tokenize(text: str) -> list[str]:
    """Normalize and tokenize text into word tokens (Spanish + English)."""
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9áéíóúñüÁÉÍÓÚÑÜ]+", text)]


def _sentences(text: str) -> list[str]:
    """Split text into sentences by terminal punctuation."""
    parts = re.split(r"(?<=[.!?¿¡])\s+", text.strip())
    return [s for s in parts if s]


# ─── Core data model ─────────────────────────────────────────────────────────

@dataclass
class LinguisticEntropyReport:
    # Raw counts
    char_count: int = 0
    word_count: int = 0
    sentence_count: int = 0
    unique_words: int = 0

    # Shannon entropies
    char_entropy: float = 0.0
    word_entropy: float = 0.0
    bigram_entropy: float = 0.0
    trigram_entropy: float = 0.0

    # Lexical diversity
    ttr: float = 0.0                     # Type-Token Ratio
    mattr: float = 0.0                   # Moving Average TTR (window=50)

    # Sentence metrics
    avg_sentence_length: float = 0.0     # words per sentence
    sentence_length_variance: float = 0.0

    # Burstiness (Goh-Barabási): B ∈ [-1, 1]
    # B = 1.0 → highly bursty (sporadic unique usage)
    # B = 0.0 → Poisson-like
    # B = -1.0 → hyper-regular (robotic repetition)
    burstiness: float = 0.0

    # Context rot: rolling window entropy delta
    context_rot_score: Decimal = 0.0       # 0.0 = no rot, 1.0 = maximum decay

    # Slop
    slop_weight_total: float = 0.0
    slop_instances: list[dict[str, Any]] = field(default_factory=list)
    slop_density: float = 0.0            # slop_weight / word_count

    # Final composite
    exergy_score: Decimal = 0.0            # 0.0 = pure anergy, 1.0 = max exergy

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Round floats for clean output
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, 4)
        # Convenience computed field for CLI consumers
        d["slop_instances_count"] = len(self.slop_instances)
        return d



# ─── Detector ────────────────────────────────────────────────────────────────

class LinguisticEntropyDetector:
    """
    Full-spectrum linguistic entropy analyzer.
    Measures information density, redundancy, and anergy across
    char/word/bigram/trigram levels plus structural metrics.
    """

    def __init__(self) -> None:
        self._compiled_slop: list[tuple[re.Pattern[str], float]] = [
            (re.compile(pattern, re.IGNORECASE), weight)
            for pattern, weight in _SLOP_PATTERNS
        ]

    # ── Shannon utilities ───────────────────────────────────────────────

    @staticmethod
    def _shannon(items: list[str]) -> float:
        if not items:
            return 0.0
        counts = Counter(items)
        total = len(items)
        return float(-sum(
            (c / total) * math.log2(c / total) for c in counts.values()
        ))

    def calculate_char_entropy(self, text: str) -> float:
        return round(self._shannon(list(text)), 4)

    def calculate_word_entropy(self, text: str) -> float:
        return round(self._shannon(_tokenize(text)), 4)

    def calculate_bigram_entropy(self, text: str) -> float:
        words = _tokenize(text)
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        return round(self._shannon(bigrams), 4)

    def calculate_trigram_entropy(self, text: str) -> float:
        words = _tokenize(text)
        trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)]
        return round(self._shannon(trigrams), 4)

    # ── Lexical diversity ───────────────────────────────────────────────

    @staticmethod
    def calculate_ttr(words: list[str]) -> float:
        if not words:
            return 0.0
        return round(len(set(words)) / len(words), 4)

    @staticmethod
    def calculate_mattr(words: list[str], window: int = 50) -> float:
        """Moving Average Type-Token Ratio — robust to text length."""
        if len(words) < window:
            if not words:
                return 0.0
            return round(len(set(words)) / len(words), 4)
        ttrs = [
            len(set(words[i:i + window])) / window
            for i in range(len(words) - window + 1)
        ]
        return round(sum(ttrs) / len(ttrs), 4)

    # ── Sentence metrics ────────────────────────────────────────────────

    @staticmethod
    def _sentence_metrics(text: str) -> tuple[float, float]:
        """Returns (avg_sentence_length_words, variance)."""
        sents = _sentences(text)
        if not sents:
            return 0.0, 0.0
        lengths = [len(_tokenize(s)) for s in sents]
        avg = statistics.mean(lengths)
        var = statistics.pvariance(lengths) if len(lengths) > 1 else 0.0
        return round(avg, 4), round(var, 4)

    # ── Burstiness (Goh-Barabási) ───────────────────────────────────────

    @staticmethod
    def _burstiness(words: list[str]) -> float:
        """
        Measures inter-event time burstiness of word recurrence.
        Positive burstiness = unique/rare usage. Negative = robotic repetition.
        Formula: B = (σ - μ) / (σ + μ), where σ,μ are std/mean of inter-event gaps.
        """
        if len(words) < 4:
            return 0.0
        positions: dict[str, list[int]] = {}
        for i, w in enumerate(words):
            positions.setdefault(w, []).append(i)

        gaps: list[float] = []
        for pos_list in positions.values():
            if len(pos_list) > 1:
                for j in range(len(pos_list) - 1):
                    gaps.append(float(pos_list[j + 1] - pos_list[j]))

        if len(gaps) < 2:
            return 0.0
        mu = statistics.mean(gaps)
        sigma = statistics.pstdev(gaps)
        if (sigma + mu) == 0:
            return 0.0
        return round((sigma - mu) / (sigma + mu), 4)

    # ── Context rot ─────────────────────────────────────────────────────

    @staticmethod
    def _context_rot(text: str, window_size: int = 100) -> float:
        """
        Measures entropy decay across rolling windows.
        High rot score = entropy is dropping as text progresses (repetition creeping in).
        Returns a score in [0.0, 1.0].
        """
        words = _tokenize(text)
        if len(words) < window_size * 2:
            return 0.0

        windows: list[float] = []
        for i in range(0, len(words) - window_size, window_size // 2):
            chunk = words[i:i + window_size]
            counts = Counter(chunk)
            total = len(chunk)
            h = -sum((c / total) * math.log2(c / total) for c in counts.values())
            windows.append(h)

        if len(windows) < 2:
            return 0.0

        # Compute the cumulative decay: how much entropy drops from first to last window
        first_half = windows[:len(windows) // 2]
        second_half = windows[len(windows) // 2:]
        h_first = sum(first_half) / len(first_half)
        h_second = sum(second_half) / len(second_half)

        if h_first == 0:
            return 0.0
        decay = max(0.0, (h_first - h_second) / h_first)
        return round(min(decay, 1.0), 4)

    # ── Slop detection ──────────────────────────────────────────────────

    def detect_slop(self, text: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for pattern, weight in self._compiled_slop:
            for match in pattern.finditer(text):
                results.append({
                    "pattern": pattern.pattern,
                    "matched_text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "severity_weight": weight,
                })
        return results

    # ── Full analysis ───────────────────────────────────────────────────

    def analyze(self, text: str) -> LinguisticEntropyReport:
        """
        Full-spectrum linguistic entropy analysis.
        Returns a LinguisticEntropyReport dataclass.
        """
        words = _tokenize(text)
        sents = _sentences(text)
        slop_instances = self.detect_slop(text)

        slop_weight_total = sum(s["severity_weight"] for s in slop_instances)
        slop_density = round(slop_weight_total / max(len(words), 1), 4)

        avg_sl, var_sl = self._sentence_metrics(text)

        report = LinguisticEntropyReport(
            char_count=len(text),
            word_count=len(words),
            sentence_count=len(sents),
            unique_words=len(set(words)),
            char_entropy=self.calculate_char_entropy(text),
            word_entropy=self.calculate_word_entropy(text),
            bigram_entropy=self.calculate_bigram_entropy(text),
            trigram_entropy=self.calculate_trigram_entropy(text),
            ttr=self.calculate_ttr(words),
            mattr=self.calculate_mattr(words),
            avg_sentence_length=avg_sl,
            sentence_length_variance=var_sl,
            burstiness=self._burstiness(words),
            context_rot_score=self._context_rot(text),
            slop_weight_total=round(slop_weight_total, 4),
            slop_instances=slop_instances,
            slop_density=slop_density,
        )

        report.exergy_score = self._compute_exergy(report)
        return report

    @staticmethod
    def _compute_exergy(r: LinguisticEntropyReport) -> float:
        """
        Composite exergy score [0.0, 1.0].
        Penalty framework:
          - Slop density      → max -0.40
          - Word entropy      → max -0.20
          - Burstiness        → max -0.15 (hyper-regular = low B)
          - Context rot       → max -0.15
          - MATTR             → max -0.10
        """
        exergy: float = 1.0

        # — Slop density penalty —
        exergy -= min(r.slop_density * 4.0, 0.40)

        # — Word entropy penalty (long texts only: >30 words) —
        if r.word_count >= 30:
            if r.word_entropy < 3.0:
                exergy -= 0.20
            elif r.word_entropy < 4.0:
                exergy -= 0.12
            elif r.word_entropy < 4.5:
                exergy -= 0.06

        # — Burstiness penalty: very negative burstiness = robotic repetition —
        if r.burstiness < -0.5:
            exergy -= 0.15
        elif r.burstiness < -0.2:
            exergy -= 0.08

        # — Context rot penalty —
        exergy -= r.context_rot_score * 0.15

        # — MATTR penalty (lexical stagnation in long texts) —
        if r.word_count > 100 and r.mattr < 0.40:
            exergy -= 0.10
        elif r.word_count > 50 and r.mattr < 0.50:
            exergy -= 0.05

        return round(max(0.0, min(1.0, exergy)), 4)
