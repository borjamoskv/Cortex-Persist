import tempfile
import os

from cortex.verification.frontend_oracle import FrontendOracle


def test_analyze_file_not_found():
    oracle = FrontendOracle()
    violations = oracle.analyze_file("nonexistent_file.js")
    assert len(violations) == 0


def test_analyze_file_html_complex_handler():
    oracle = FrontendOracle()
    content = """
    <html>
    <script>
    function handleUpdate() {
        if (a) {
            if (b) {
                for (let i=0; i<10; i++) {
                    if (c && d || e) {
                        console.log(f ? 1 : 2);
                    }
                }
            }
        }
    }
    </script>
    </html>
    """
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(content)
        filepath = f.name

    try:
        violations = oracle.analyze_file(filepath)
        assert len(violations) == 1
        assert violations[0]["function"] == "handleUpdate"
        assert violations[0]["file"] == filepath
        assert violations[0]["complexity"] >= 5
    finally:
        os.remove(filepath)


def test_analyze_file_js_simple_handler():
    oracle = FrontendOracle()
    content = """
    const myListener = () => {
        if (a) {
            console.log("ok");
        }
    }
    """
    with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
        f.write(content)
        filepath = f.name

    try:
        violations = oracle.analyze_file(filepath)
        assert len(violations) == 0
    finally:
        os.remove(filepath)


def test_analyze_file_js_complex_handler_const():
    oracle = FrontendOracle()
    content = """
    const complexListener = (event) => {
        if (a) {
            if (b) {
                while (c) {
                    if (d && e) {
                        catch (err) {
                            switch (f) {
                                case 1: break;
                            }
                        }
                    }
                }
            }
        }
    }
    """
    with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
        f.write(content)
        filepath = f.name

    try:
        violations = oracle.analyze_file(filepath)
        assert len(violations) == 1
        assert violations[0]["function"] == "complexListener"
        assert violations[0]["complexity"] >= 5
    finally:
        os.remove(filepath)


def test_analyze_file_js_complex_non_handler():
    oracle = FrontendOracle()
    content = """
    function computeSomething() {
        if (a) {
            if (b) {
                for (let i=0; i<10; i++) {
                    if (c && d || e) {
                        console.log(f ? 1 : 2);
                    }
                }
            }
        }
    }
    """
    with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
        f.write(content)
        filepath = f.name

    try:
        violations = oracle.analyze_file(filepath)
        assert len(violations) == 0  # Function name doesn't contain handler, listener, update
    finally:
        os.remove(filepath)


def test_extract_block_fallback():
    # Test _extract_block fallback
    oracle = FrontendOracle()
    block = oracle._extract_block("{ incomplete block ", 0)
    assert block == "{ incomplete block "


def test_regex_no_group_match():
    # Force a match where both group 1 and group 2 are empty/none.
    oracle = FrontendOracle()
    content = """
    const  = () => { }
    function () { }
    """
    with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
        f.write(content)
        filepath = f.name

    try:
        violations = oracle.analyze_file(filepath)
        assert len(violations) == 0
    finally:
        os.remove(filepath)
