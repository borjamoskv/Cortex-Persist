import time

from cortex.axioms.topological_id import SovereignFlake


def test_flake_sequence_increment():
    gen = SovereignFlake(node_id=42)
    id1 = gen.next_id()
    id2 = gen.next_id()
    assert id2 > id1

    # Even if we force a very tight loop, it should strictly increase
    ids = set()
    for _ in range(1000):
        ids.add(gen.next_id())
    assert len(ids) == 1000


def test_flake_lexicographical_sorting():
    gen = SovereignFlake(node_id=1)

    id1 = gen.next_lexicographic_id()
    time.sleep(0.002)  # force sleep across real ms
    id2 = gen.next_lexicographic_id()

    assert isinstance(id1, str)
    assert len(id1) == 19
    assert id2 > id1


def test_flake_backward_clock_drift():
    # Simulate an NTP sync backwards
    gen = SovereignFlake(node_id=1)

    curr_time = int(time.time() * 1000)
    gen.last_timestamp = curr_time + 5000  # "Future" timestamp

    id1 = gen.next_id()
    id2 = gen.next_id()

    assert id2 > id1

    # Reconstruct id to verify the logic timestamp froze but sequence advanced
    # Last 12 bits are sequence
    seq1 = id1 & 0xFFF
    seq2 = id2 & 0xFFF
    assert seq2 == seq1 + 1
