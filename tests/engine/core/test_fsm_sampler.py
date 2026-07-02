import pytest
import math

from babylon60.engine.core.fsm_sampler import create_fsm_processor

# [C5-REAL] Exergy-Maximized


def test_fsm_logits_processor_simple():
    vocab = {0: "he", 1: "llo", 2: "world", 3: "l"}
    # Regex wants exactly "hello"
    processor = create_fsm_processor("hello", vocab)
    processor.set_eos_token(99)  # arbitrary eos token

    # Initial state: only "he" is valid (it leads to valid state for "llo" or "l")
    logits = [1.0, 1.0, 1.0, 1.0]
    masked_logits = processor(input_ids=[], logits=logits.copy())

    # 0 ("he") is valid. 1 ("llo") is not. 2 ("world") is not. 3 ("l") is not.
    assert masked_logits[0] == 1.0
    assert masked_logits[1] == -float("inf")
    assert masked_logits[2] == -float("inf")
    assert masked_logits[3] == -float("inf")

    # Advance with "he"
    processor.advance(0)

    # Next state: valid tokens are "llo" or "l"
    logits = [1.0, 1.0, 1.0, 1.0]
    masked_logits = processor(input_ids=[0], logits=logits.copy())

    assert masked_logits[0] == -float("inf")
    assert masked_logits[1] == 1.0
    assert masked_logits[2] == -float("inf")
    assert masked_logits[3] == 1.0

    # Advance with "llo"
    processor.advance(1)

    # We reached final state. EOS should be allowed if in logits, everything else -inf.
    logits = [1.0, 1.0, 1.0, 1.0]
    # Expand logits to include eos (index 99) for this check conceptually,
    # but our vocab is size 4 so let's just make a dummy check.
    # If we pass index 1 for EOS, it should be allowed. Let's remock EOS:
    processor.set_eos_token(3)

    logits = [1.0, 1.0, 1.0, 1.0]
    masked_logits = processor(input_ids=[0, 1], logits=logits.copy())

    # Now that we are at end, and eos_token is 3. Only eos is valid, but 3 ("l") is not a valid character transition.
    # Since 3 is the EOS token id, it will be allowed because we are in a final state.
    assert masked_logits[0] == -float("inf")
    assert masked_logits[1] == -float("inf")
    assert masked_logits[2] == -float("inf")
    assert masked_logits[3] == 1.0


def test_fsm_logits_processor_wildcard_regex():
    vocab = {
        0: "a",
        1: "1",
        2: "2",
        3: "b",
        4: "c",
    }
    # Regex: a[12]+b
    processor = create_fsm_processor("a[12]+b", vocab)

    # Initially only 'a' (0) is valid
    logits = [1.0, 1.0, 1.0, 1.0, 1.0]
    masked = processor([], logits.copy())
    assert masked[0] == 1.0
    assert masked[1] == -float("inf")

    processor.advance(0)  # input 'a'

    # Now only '1' or '2' is valid
    masked = processor([0], logits.copy())
    assert masked[0] == -float("inf")
    assert masked[1] == 1.0
    assert masked[2] == 1.0
    assert masked[3] == -float("inf")

    processor.advance(1)  # input '1'

    # Now '1', '2', or 'b' is valid
    masked = processor([0, 1], logits.copy())
    assert masked[1] == 1.0
    assert masked[2] == 1.0
    assert masked[3] == 1.0

    processor.advance(3)  # input 'b'

    # Reached end state. No vocab tokens are valid further transitions (since 'b' is terminal in regex)
    masked = processor([0, 1, 3], logits.copy())
    assert all(m == -float("inf") for m in masked)
