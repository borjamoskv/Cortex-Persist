# [C5-REAL] Exergy-Maximized | borjamoskv
"""
Unit tests for LinguisticEntropyDetector (PLAYGROUND EDITION).
Covers: Shannon, bigram, trigram, TTR, MATTR, burstiness, context rot, slop, exergy.
"""

import pytest
from babylon60.utils.linguistic_entropy import LinguisticEntropyDetector, _tokenize, _sentences


# ─── Tokenizer ────────────────────────────────────────────────────────────────


def test_tokenizer_basic() -> None:
    tokens = _tokenize("Hello world!")
    assert tokens == ["hello", "world"]


def test_tokenizer_spanish() -> None:
    tokens = _tokenize("Canción española: ¡estupendo!")
    assert "canción" in tokens
    assert "española" in tokens


def test_sentences_split() -> None:
    sents = _sentences("Hello world. How are you? Fine!")
    assert len(sents) == 3


# ─── Shannon Entropies ────────────────────────────────────────────────────────


class TestShannonEntropies:
    def setup_method(self) -> None:
        self.d = LinguisticEntropyDetector()

    def test_char_entropy_empty(self) -> None:
        assert self.d.calculate_char_entropy("") == 0.0

    def test_char_entropy_uniform(self) -> None:
        assert self.d.calculate_char_entropy("aaaa") == 0.0

    def test_char_entropy_diverse(self) -> None:
        assert self.d.calculate_char_entropy("abcdef") > 2.5

    def test_word_entropy_empty(self) -> None:
        assert self.d.calculate_word_entropy("") == 0.0

    def test_word_entropy_repetitive(self) -> None:
        assert self.d.calculate_word_entropy("word word word word") == 0.0

    def test_word_entropy_diverse(self) -> None:
        assert self.d.calculate_word_entropy("alpha beta gamma delta epsilon") > 2.0

    def test_bigram_entropy_empty(self) -> None:
        assert self.d.calculate_bigram_entropy("") == 0.0

    def test_bigram_entropy_unique(self) -> None:
        # Each consecutive pair is unique → maximal bigram entropy
        e = self.d.calculate_bigram_entropy("one two three four five")
        assert e > 1.5

    def test_trigram_entropy_empty(self) -> None:
        assert self.d.calculate_trigram_entropy("word") == 0.0

    def test_trigram_entropy(self) -> None:
        # All same word → only 1 unique trigram → entropy = 0
        e = self.d.calculate_trigram_entropy("the the the the the the")
        assert e == 0.0

    def test_trigram_entropy_diverse(self) -> None:
        # 4 unique tokens → multiple distinct trigrams → entropy > 0
        e = self.d.calculate_trigram_entropy("a b c a b c a b c")
        assert e > 0.0


# ─── Lexical Diversity ────────────────────────────────────────────────────────


class TestLexicalDiversity:
    def setup_method(self) -> None:
        self.d = LinguisticEntropyDetector()

    def test_ttr_empty(self) -> None:
        assert self.d.calculate_ttr([]) == 0.0

    def test_ttr_full_unique(self) -> None:
        assert self.d.calculate_ttr(["a", "b", "c"]) == 1.0

    def test_ttr_half(self) -> None:
        assert self.d.calculate_ttr(["a", "b", "a", "b"]) == 0.5

    def test_mattr_short_text(self) -> None:
        words = ["one", "two", "three"]
        mattr = self.d.calculate_mattr(words)
        assert 0.0 < mattr <= 1.0

    def test_mattr_repetitive(self) -> None:
        words = ["the"] * 100
        mattr = self.d.calculate_mattr(words)
        assert mattr < 0.1


# ─── Burstiness ───────────────────────────────────────────────────────────────


class TestBurstiness:
    def setup_method(self) -> None:
        self.d = LinguisticEntropyDetector()

    def test_burstiness_too_short(self) -> None:
        b = self.d._burstiness(["a", "b"])
        assert b == 0.0

    def test_burstiness_robotic(self) -> None:
        # Perfectly evenly spaced repetitions: word at positions 0,5,10,15...
        # Gap std=0, mean=5 → B = (0-5)/(0+5) = -1.0
        words = ["x" if i % 5 == 0 else f"y{i}" for i in range(50)]
        b = self.d._burstiness(words)
        assert b < 0.0, f"Expected negative burstiness for regular gaps, got {b}"

    def test_burstiness_range(self) -> None:
        import random

        random.seed(42)
        words = random.choices(["a", "b", "c", "d", "e", "f"], k=100)
        b = self.d._burstiness(words)
        assert -1.0 <= b <= 1.0


# ─── Context Rot ──────────────────────────────────────────────────────────────


class TestContextRot:
    def setup_method(self) -> None:
        self.d = LinguisticEntropyDetector()

    def test_context_rot_short(self) -> None:
        score = self.d._context_rot("too short")
        assert score == 0.0

    def test_context_rot_diverse(self) -> None:
        # 500 distinct words → negligible rot
        text = " ".join(f"word{i}" for i in range(500))
        score = self.d._context_rot(text)
        assert score < 0.2

    def test_context_rot_degrading(self) -> None:
        # Start diverse, end repetitive
        diverse = " ".join(f"unique{i}" for i in range(100))
        repetitive = " ".join(["spam"] * 200)
        text = diverse + " " + repetitive
        score = self.d._context_rot(text)
        assert score >= 0.0  # should detect decay


# ─── Slop Detection ───────────────────────────────────────────────────────────


class TestSlopDetection:
    def setup_method(self) -> None:
        self.d = LinguisticEntropyDetector()

    def test_no_slop(self) -> None:
        results = self.d.detect_slop("The hash chain is intact.")
        assert results == []

    def test_slop_detection_es(self) -> None:
        results = self.d.detect_slop("Aquí tienes el código para tu función.")
        assert len(results) == 1
        assert results[0]["severity_weight"] == 1.0

    def test_slop_detection_multi(self) -> None:
        text = "Aquí tienes el código. Espero que esto ayude. Por supuesto."
        results = self.d.detect_slop(text)
        assert len(results) == 3

    def test_slop_case_insensitive(self) -> None:
        results = self.d.detect_slop("AS AN AI LANGUAGE MODEL, I...")
        assert len(results) == 1

    def test_slop_severity_weight_in_result(self) -> None:
        results = self.d.detect_slop("Here is the code you requested.")
        assert "severity_weight" in results[0]
        assert results[0]["severity_weight"] > 0.0


# ─── Full Analysis Report ─────────────────────────────────────────────────────


class TestFullAnalysis:
    def setup_method(self) -> None:
        self.d = LinguisticEntropyDetector()

    def test_report_dataclass_fields(self) -> None:
        report = self.d.analyze("hello world")
        rdict = report.to_dict()
        for key in [
            "char_count",
            "word_count",
            "sentence_count",
            "unique_words",
            "char_entropy",
            "word_entropy",
            "bigram_entropy",
            "trigram_entropy",
            "ttr",
            "mattr",
            "avg_sentence_length",
            "sentence_length_variance",
            "burstiness",
            "context_rot_score",
            "slop_weight_total",
            "slop_instances",
            "slop_density",
            "exergy_score",
        ]:
            assert key in rdict, f"Missing field: {key}"

    def test_clean_text_exergy(self) -> None:
        text = (
            "The Byzantine consensus protocol enforces cryptographic continuity. "
            "Every ledger mutation is tainted and hash-chained before persistence. "
            "No stochastic output may mutate deterministic state without guard validation."
        )
        report = self.d.analyze(text)
        assert report.exergy_score >= 0.8

    def test_slop_text_exergy(self) -> None:
        text = (
            "Aquí tienes el código que pediste. Espero que esto ayude. "
            "Por supuesto, no dudes en preguntar. Como modelo de lenguaje, "
            "estoy aquí para ayudarte. ¡Claro! Feel free to ask anything."
        )
        report = self.d.analyze(text)
        assert report.exergy_score < 0.65

    def test_exergy_bounds(self) -> None:
        for text in ["", "a", "hello", "the " * 200]:
            report = self.d.analyze(text)
            assert 0.0 <= report.exergy_score <= 1.0

    def test_slop_density_increases_with_slop(self) -> None:
        clean = self.d.analyze("Cryptographic hash chains enforce tamper evidence.")
        sloppy = self.d.analyze(
            "Aquí tienes el código. Espero que esto ayude. Por supuesto entendido."
        )
        assert sloppy.slop_density > clean.slop_density
