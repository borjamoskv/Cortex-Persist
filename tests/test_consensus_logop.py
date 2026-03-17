import math

import pytest

pytestmark = pytest.mark.asyncio


async def test_logop_consensus_math():
    from cortex.consensus.manager import _logit, _sigmoid

    # Test bounds
    assert math.isclose(_logit(0.5), 0.0, abs_tol=1e-5)
    assert _logit(0.99) > 0
    assert _logit(0.01) < 0

    assert math.isclose(_sigmoid(0.0), 0.5, abs_tol=1e-5)

    # Epistemic veto test
    # 3 highly unreliable agents vote TRUE
    # 1 highly reliable agent votes FALSE

    votes = [
        (1, 0.1, 0.2),  # vote, vote_weight, reputation
        (1, 0.2, 0.1),
        (1, 0.1, 0.1),
        (-1, 0.9, 0.9),  # The expert veto
    ]

    score_sum = 0.0
    for vote_val, w1, w2 in votes:
        p = 0.99 if vote_val > 0 else 0.01
        rel = max(w1, w2)
        w = rel**2
        score_sum += w * _logit(p)

    prob_true = _sigmoid(score_sum)
    score = prob_true * 2.0

    # The expert (-1) should completely overwhelm the unreliable true votes
    assert prob_true < 0.5
    assert score < 1.0
