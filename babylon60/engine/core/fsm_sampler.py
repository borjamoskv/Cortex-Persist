from __future__ import annotations

from typing import Optional

from babylon60.engine.core.fsm_regex import DFA, compile_regex

# [C5-REAL] Exergy-Maximized
"""
FSM Sampler / Logit Processor for Regex-guided generation.

Enforces pure determinism by masking logits of tokens that do not
constitute a valid transition in the DFA.
"""


class FSMVocabIndexer:
    """
    Precomputes or lazily computes the valid transitions for all tokens in a vocabulary
    against a given DFA.
    """

    def __init__(self, dfa: DFA, vocab: dict[int, str]):
        self.dfa = dfa
        self.vocab = vocab
        # Current DFA State -> (Allowed Token IDs -> Next DFA State)
        self._transitions: dict[int, dict[int, int]] = {}

    def get_valid_tokens(self, state_id: int) -> dict[int, int]:
        """
        Returns a map of {token_id: next_state_id} for all valid tokens from `state_id`.
        Computes lazily.
        """
        if state_id in self._transitions:
            return self._transitions[state_id]

        valid_map = {}
        for token_id, token_str in self.vocab.items():
            next_state = self._trace_token(state_id, token_str)
            if next_state is not None:
                valid_map[token_id] = next_state

        self._transitions[state_id] = valid_map
        return valid_map

    def _trace_token(self, start_state: int, token_str: str) -> Optional[int]:
        """
        Traces a string token character by character through the DFA.
        Returns the resulting state ID if valid, otherwise None.
        """
        current = start_state
        for char in token_str:
            if current not in self.dfa.transitions or char not in self.dfa.transitions[current]:
                return None
            current = self.dfa.transitions[current][char]
        return current


class FSMLogitsProcessor:
    """
    Injects into the generation loop to force logits to adhere to the FSM.
    """

    def __init__(self, indexer: FSMVocabIndexer):
        self.indexer = indexer
        self.current_state = self.indexer.dfa.start_state
        # For tracing the sequence of states if needed for debugging/SAGA
        self.state_history = [self.current_state]
        self._eos_token_id: Optional[int] = None

    def set_eos_token(self, eos_token_id: int):
        self._eos_token_id = eos_token_id

    def __call__(self, input_ids: list[int], logits: list[float]) -> list[float]:
        """
        HuggingFace/Local inference compatible signature.
        `logits` is expected to be a 1D list/array of size len(vocab).
        """
        valid_transitions = self.indexer.get_valid_tokens(self.current_state)

        # Determine if we can generate EOS (only if current state is final)
        can_eos = self.indexer.dfa.states[self.current_state].is_final

        for token_id in range(len(logits)):
            if token_id == self._eos_token_id:
                if not can_eos:
                    logits[token_id] = -float("inf")
            elif token_id not in valid_transitions:
                logits[token_id] = -float("inf")

        return logits

    def advance(self, token_id: int):
        """
        Advances the FSM state given the sampled token.
        MUST be called after a token is sampled.
        """
        valid_transitions = self.indexer.get_valid_tokens(self.current_state)
        if token_id not in valid_transitions:
            if (
                token_id == self._eos_token_id
                and self.indexer.dfa.states[self.current_state].is_final
            ):
                # Valid EOS transition
                return
            raise ValueError(
                f"[FSM-CORRUPTION] Token {token_id} sampled but invalid from state {self.current_state}. "
                "Logits masking failed or was bypassed."
            )

        self.current_state = valid_transitions[token_id]
        self.state_history.append(self.current_state)


def create_fsm_processor(regex_pattern: str, vocab: dict[int, str]) -> FSMLogitsProcessor:
    """
    Factory function for building the complete Regex FSM pipeline.
    """
    # Extract unique characters from the vocabulary to build the DFA alphabet
    vocab_chars: set[str] = set()
    for token in vocab.values():
        vocab_chars.update(token)

    dfa = compile_regex(regex_pattern, vocab_chars)
    indexer = FSMVocabIndexer(dfa, vocab)
    return FSMLogitsProcessor(indexer)
