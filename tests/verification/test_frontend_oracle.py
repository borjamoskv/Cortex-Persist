# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import patch, mock_open, MagicMock
from babylon60.verification.frontend_oracle import FrontendOracle


@pytest.fixture
def oracle():
    return FrontendOracle()


def test_analyze_file_html(oracle):
    html_content = """
    <html>
    <body>
    <script>
    function handleUpdate() {
        if (true) {
            if (true) {
                if (true) {
                    if (true) {
                        if (true) {
                            console.log('complex');
                        }
                    }
                }
            }
        }
    }
    </script>
    </body>
    </html>
    """
    with patch("builtins.open", mock_open(read_data=html_content)):
        violations = oracle.analyze_file("test.html")
    assert len(violations) == 1
    assert violations[0]["function"] == "handleUpdate"
    assert violations[0]["complexity"] == 5


def test_analyze_file_js(oracle):
    js_content = """
    const myListener = () => {
        for(let i = 0; i < 10; i++) {
            if (i % 2 === 0) {
                while(false) {}
                try {} catch(e) {}
                const a = b ? c : d;
            }
        }
    }
    function normalFunction() {
        if (true) {}
    }
    """
    with patch("builtins.open", mock_open(read_data=js_content)):
        violations = oracle.analyze_file("test.js")
    assert len(violations) == 1
    assert violations[0]["function"] == "myListener"
    assert violations[0]["complexity"] == 5


def test_analyze_file_oserror(oracle):
    with patch("builtins.open", side_effect=OSError):
        violations = oracle.analyze_file("missing.js")
    assert len(violations) == 0


def test_extract_block_fallback(oracle):
    # Test fallback branch in _extract_block where brackets don't match
    text = "function test() { if (true) return; "
    block = oracle._extract_block(text, text.index("{"))
    assert block == "{ if (true) return; "


def test_empty_function_name(oracle):
    # Mock re.finditer to return a match with no groups to hit `if not func_name: continue`
    with patch("cortex.verification.frontend_oracle.re.compile") as mock_compile:
        mock_pattern = MagicMock()
        mock_match = MagicMock()
        mock_match.group.return_value = None
        mock_pattern.finditer.return_value = [mock_match]
        mock_compile.return_value = mock_pattern

        with patch("builtins.open", mock_open(read_data="function() {}")):
            oracle.analyze_file("test.js")


def test_complexity_operators(oracle):
    js_content = """
    function handleComplexity() {
        if (a && b || c) {
            switch(d) {
                case 1: break;
            }
        } else if (e) {
        }
    }
    """
    with patch("builtins.open", mock_open(read_data=js_content)):
        violations = oracle.analyze_file("test.js")
    assert len(violations) == 1
    assert violations[0]["complexity"] == 6
