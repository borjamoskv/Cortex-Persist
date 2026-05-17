import pytest
from cortex.memory.sqlite_vec_store import cortex_decay

def test_cortex_decay_diamond():
    # If is_diamond is true, it should always return 1.0 regardless of age
    assert cortex_decay(1, 100.0, 200.0, 10.0) == 1.0
    assert cortex_decay(True, 100.0, 200.0, 10.0) == 1.0

def test_cortex_decay_future_timestamp():
    # If timestamp is in the future (age < 0), it should cap at 0 and return 1.0
    assert cortex_decay(0, 200.0, 100.0, 10.0) == 1.0

def test_cortex_decay_half_life():
    # After one half life, value should be 0.5
    assert cortex_decay(0, 100.0, 110.0, 10.0) == 0.5
    # After two half lives, value should be 0.25
    assert cortex_decay(0, 100.0, 120.0, 10.0) == 0.25
    # After zero time, value should be 1.0
    assert cortex_decay(0, 100.0, 100.0, 10.0) == 1.0
