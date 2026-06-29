# [C5-REAL] Exergy-Maximized

from babylon60.tools.blackbox_harness import ProvenanceAuditor, SingleResult, PROVENANCE_BASELINES

def test_empty_results():
    auditor = ProvenanceAuditor(PROVENANCE_BASELINES)
    analysis = auditor.analyze([])
    assert analysis["status"] == "insufficient_data"
    assert analysis["identity_claim"] == "not_supported"

def test_profile_alpha_classification():
    # Perfil opaco Alpha: itl_ms = 22.5, char_ratio = 3.8, md_density = 0.12, lexical_bias = 0.04
    text = "#" * 64 + " delve certainly tapestry " + "the " * 80 + "a" * 126
    run = SingleResult(
        prompt_sha256="abc",
        status_code=200,
        rejected=False,
        error_type=None,
        latency_ms=3172.5,
        ttft_ms=0.0,
        completion_tokens=141,
        tokens_per_sec=44.44,
        json_valid=False,
        exact_match=None,
        response_text=text,
        response_preview=text[:200],
        timestamp_iso="2026-06-29"
    )
    auditor = ProvenanceAuditor(PROVENANCE_BASELINES)
    analysis = auditor.analyze([run])
    assert analysis["nearest_profile"] == "profile_alpha"
    assert analysis["similarity_scores"]["profile_alpha"] > 0.45

def test_profile_beta_classification():
    # Perfil opaco Beta: itl_ms = 10.2, char_ratio = 4.2, md_density = 0.05, lexical_bias = 0.02
    text = "#" * 21 + " certainly " + "the " * 72 + "a" * 94
    run = SingleResult(
        prompt_sha256="def",
        status_code=200,
        rejected=False,
        error_type=None,
        latency_ms=1020.0,
        ttft_ms=0.0,
        completion_tokens=100,
        tokens_per_sec=98.0,
        json_valid=False,
        exact_match=None,
        response_text=text,
        response_preview=text[:200],
        timestamp_iso="2026-06-29"
    )
    auditor = ProvenanceAuditor(PROVENANCE_BASELINES)
    analysis = auditor.analyze([run])
    assert analysis["nearest_profile"] == "profile_beta"
    assert analysis["similarity_scores"]["profile_beta"] > 0.45

def test_profile_gamma_classification():
    # Perfil opaco Gamma: itl_ms = 15.8, char_ratio = 4.0, md_density = 0.08, lexical_bias = 0.03
    text = "#" * 32 + " tapestry certainly " + "the " * 70 + "a" * 69
    run = SingleResult(
        prompt_sha256="ghi",
        status_code=200,
        rejected=False,
        error_type=None,
        latency_ms=1580.0,
        ttft_ms=0.0,
        completion_tokens=100,
        tokens_per_sec=63.29,
        json_valid=False,
        exact_match=None,
        response_text=text,
        response_preview=text[:200],
        timestamp_iso="2026-06-29"
    )
    auditor = ProvenanceAuditor(PROVENANCE_BASELINES)
    analysis = auditor.analyze([run])
    assert analysis["nearest_profile"] == "profile_gamma"
    assert analysis["similarity_scores"]["profile_gamma"] > 0.45

