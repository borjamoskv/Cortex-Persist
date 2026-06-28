import os
import pytest


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("CORTEX_TESTING", "1")


def test_rust_bridge_initialization():
    from cortex.embeddings.rust_bridge import RustNativeEmbeddings

    # Should not raise FileNotFoundError because CORTEX_TESTING is set
    engine = RustNativeEmbeddings(
        model_path="dummy_model.onnx", tokenizer_path="dummy_tokenizer.json"
    )

    assert engine.model_path == "dummy_model.onnx"
    assert engine.session is None


def test_rust_bridge_generation():
    from cortex.embeddings.rust_bridge import RustNativeEmbeddings

    engine = RustNativeEmbeddings(
        model_path="dummy_model.onnx", tokenizer_path="dummy_tokenizer.json"
    )

    texts = ["Zero anergy is death", "The 99.99 state is already the invariant"]

    embeddings = engine.generate(texts)

    # Due to testing mock, it generates random arrays of dimension 384
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384

    # Test empty input
    assert engine.generate([]) == []
