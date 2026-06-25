from cortex.guards.zk_guard import CommitRevealProtocol

def test_commit_reveal_valid():
    payload = {"fact": "AI is accelerating", "confidence": 0.99}
    
    commit_hash, nonce = CommitRevealProtocol.generate_commit(payload)
    assert len(commit_hash) == 64
    assert len(nonce) == 64
    
    is_valid = CommitRevealProtocol.verify_commit(commit_hash, nonce, payload)
    assert is_valid is True

def test_commit_reveal_invalid_payload():
    payload = {"fact": "AI is accelerating", "confidence": 0.99}
    fake_payload = {"fact": "AI is accelerating", "confidence": 0.10}
    
    commit_hash, nonce = CommitRevealProtocol.generate_commit(payload)
    is_valid = CommitRevealProtocol.verify_commit(commit_hash, nonce, fake_payload)
    assert is_valid is False
    
def test_commit_reveal_invalid_nonce():
    payload = {"fact": "AI is accelerating", "confidence": 0.99}
    
    commit_hash, nonce = CommitRevealProtocol.generate_commit(payload)
    fake_nonce = "00" * 32
    is_valid = CommitRevealProtocol.verify_commit(commit_hash, fake_nonce, payload)
    assert is_valid is False
