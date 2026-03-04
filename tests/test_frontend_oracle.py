import os
import tempfile

from cortex.verification.frontend_oracle import FrontendOracle


def test_frontend_oracle_detects_complexity():
    oracle = FrontendOracle()

    html_content = """
    <html>
    <script>
    function handleLiveUpdate(data) {
        if (data) {
            if (data.type == 'A') {
                for (let i = 0; i < 10; i++) {
                    if (data.value && data.value > 0) {
                        console.log('complex');
                    }
                }
            } else if (data.type == 'B') {
                while(true) {
                    break;
                }
            }
        }
    }
    
    function handleSimple() {
        console.log("simple");
    }
    </script>
    </html>
    """
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        f.write(html_content.encode("utf-8"))
        temp_path = f.name

    try:
        violations = oracle.analyze_file(temp_path)
        assert len(violations) == 1
        assert violations[0]["function"] == "handleLiveUpdate"
        assert violations[0]["complexity"] >= 5
    finally:
        os.remove(temp_path)
