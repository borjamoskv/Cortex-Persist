from __future__ import annotations


def test_oracle_detects_no_state_change():
    from cortex.mac_maestro.oracle import VerificationOracle

    oracle = VerificationOracle(
        rescan_fn=lambda: {"button_visible": True},
        matcher_fn=lambda state: state["button_visible"] is False,
    )
    verdict = oracle.verify()

    assert verdict.verified is False
    assert verdict.reason == "state_not_changed"
