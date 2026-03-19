#!/usr/bin/env python3
import re

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


try:
    import nltk

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


class ChomskyEngine:
    def __init__(self, spacy_model="en_core_web_sm"):
        self.nlp = None
        self.mode = "regex_fallback"

        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load(spacy_model)
                self.mode = "spacy_strict"
            except OSError:
                print(f"WARN: spaCy is installed but model '{spacy_model}' is missing.")
        elif NLTK_AVAILABLE:
            self.mode = "nltk_strict"

    def compress_spacy(self, text: str) -> dict:
        doc = self.nlp(text)

        retained_tokens = []
        proper_nouns = 0
        numbers = 0

        # We perform syntactic structural pruning
        # KEEP: PROPN (Proper Noun), NOUN, VERB, NUM, SYM, PRON (optional)
        # DROP: ADJ, ADV, DET, INTJ

        for token in doc:
            if token.pos_ == "PROPN":
                proper_nouns += 1
                retained_tokens.append(token.text)
            elif token.pos_ == "NUM":
                numbers += 1
                retained_tokens.append(token.text)
            elif token.pos_ in ["NOUN", "VERB", "SYM"]:
                retained_tokens.append(token.text)
            # Punctuation generally kept for readability but we can skip some
            elif token.pos_ == "PUNCT":
                if token.text in [".", ",", "?", "!"]:
                    # Attach it to the previous token if possible
                    if retained_tokens:
                        retained_tokens[-1] = retained_tokens[-1] + token.text
                    else:
                        retained_tokens.append(token.text)
            else:
                # We drop it (ADJ, ADV, DET, ADP, CCONJ mostly)
                pass

        reconstituted = " ".join(retained_tokens)
        # cleanup spaces around punctuation
        reconstituted = re.sub(r" \.", ".", reconstituted)
        reconstituted = re.sub(r" ,", ",", reconstituted)

        original_tokens = len(text.split())
        new_tokens = len(retained_tokens)

        return {
            "compressed_payload": reconstituted.strip(),
            "tokens_saved": original_tokens - new_tokens,
            "proper_nouns_retained": proper_nouns,
            "numbers_retained": numbers,
            "ast_mode": self.mode,
        }

    def compress_nltk(self, text: str) -> dict:
        if not NLTK_AVAILABLE:
            return self.compress_fallback(text)

        try:
            tokens = nltk.word_tokenize(text)
            tagged = nltk.pos_tag(tokens)
        except LookupError:
            nltk.download("punkt")
            nltk.download("punkt_tab")
            nltk.download("averaged_perceptron_tagger_eng")
            tokens = nltk.word_tokenize(text)
            tagged = nltk.pos_tag(tokens)

        retained = []
        proper_nouns = 0
        numbers = 0

        # NLTK POS Tags:
        # NNP/NNPS (Proper Noun), NN/NNS (Noun), VB* (Verb), CD (Numeral)
        # Drop: JJ* (Adjective), RB* (Adverb), DT (Determiner)
        for word, tag in tagged:
            if tag in ["NNP", "NNPS"]:
                proper_nouns += 1
                retained.append(word)
            elif tag == "CD" or word.isdigit():
                numbers += 1
                retained.append(word)
            elif tag.startswith("NN") or tag.startswith("VB") or tag in ["SYM"]:
                retained.append(word)
            elif tag in [".", ",", ":", "$"]:
                # Attach punctuation
                if retained and tag not in ["$"]:
                    retained[-1] = retained[-1] + word
                else:
                    retained.append(word)

        reconstituted = " ".join(retained)
        reconstituted = re.sub(r" \.", ".", reconstituted)
        reconstituted = re.sub(r" ,", ",", reconstituted)

        return {
            "compressed_payload": reconstituted.strip(),
            "tokens_saved": len(tokens) - len(retained),
            "proper_nouns_retained": proper_nouns,
            "numbers_retained": numbers,
            "ast_mode": "nltk_strict",
        }

    def compress_fallback(self, text: str) -> dict:
        # Regex fallback: keep Capitalized words (pseudo-proper nouns), numbers, and tokens > 4 chars
        words = text.split()
        retained = []
        proper_nouns = 0
        numbers = 0

        for w in words:
            clean_w = re.sub(r"[^\w]", "", w)
            if clean_w.isupper() or (clean_w and clean_w[0].isupper()):
                proper_nouns += 1
                retained.append(w)
            elif clean_w.isdigit():
                numbers += 1
                retained.append(w)
            elif len(clean_w) > 4:
                # Naive heuristic to keep core verbs/nouns
                retained.append(w)

        reconstituted = " ".join(retained)
        return {
            "compressed_payload": reconstituted,
            "tokens_saved": len(words) - len(retained),
            "proper_nouns_retained": proper_nouns,
            "numbers_retained": numbers,
            "ast_mode": "regex_fallback",
        }


def compress(text: str) -> dict:
    engine = ChomskyEngine()
    if engine.mode == "spacy_strict":
        return engine.compress_spacy(text)
    elif engine.mode == "nltk_strict":
        return engine.compress_nltk(text)
    else:
        return engine.compress_fallback(text)


if __name__ == "__main__":
    import sys

    payload = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "The incredibly fast Google servers processed 5000 requests effortlessly without any critical failure."
    )
    print("ORIGINAL:", payload)
    res = compress(payload)
    print("\nCHOMSKY OMEGA RESULT:")
    for k, v in res.items():
        print(f"  {k}: {v}")
