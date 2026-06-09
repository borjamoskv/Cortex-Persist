import sys
from pathlib import Path

# Add scripts directory to path to import sovereign_scorer
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from sovereign_scorer import score


def test_sovereign_scorer():
    """Verify that sovereign scorer can analyze its own codebase and returns a valid score."""
    target_path = Path(__file__).parent / "scripts"
    
    report = score(target_path, detailed=False)
    
    # Assertions to ensure the interface contract is respected
    assert "error" not in report, f"Scorer failed: {report.get('error')}"
    assert "total_score" in report, "Report missing total_score"
    assert "verdict" in report, "Report missing verdict"
    assert "dimensions" in report, "Report missing dimensions"
    assert report["files_analyzed"] > 0, "Should have analyzed at least 1 file"
    assert 0 <= report["total_score"] <= 100, f"Score out of bounds: {report['total_score']}"
    
    print(f"✅ sovereign-code-scorer verification passed! Self-Score: {report['total_score']}/100")

if __name__ == "__main__":
    test_sovereign_scorer()
