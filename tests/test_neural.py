import sys
from unittest.mock import MagicMock

# Mock PyObjC modules before importing the engine
mock_appkit = MagicMock()
mock_appkit.NSWorkspace = MagicMock()
mock_appkit.NSPasteboard = MagicMock()
mock_appkit.NSPasteboardTypeString = "public.utf8-plain-text"

sys.modules["AppKit"] = mock_appkit
sys.modules["Foundation"] = MagicMock()
sys.modules["objc"] = MagicMock()

import pytest
from cortex.neural import NeuralIntentEngine


class MockActiveWindowSensor:
    def __init__(self, window: str):
        self.window = window

    def get_active_window(self) -> str:
        return self.window


class MockClipboardSensor:
    def __init__(self, clipboard: str):
        self.clipboard = clipboard

    def get_clipboard(self) -> str:
        return self.clipboard


@pytest.fixture
def engine(monkeypatch):
    eng = NeuralIntentEngine()

    # helper to mock sensors dynamically
    def mock_sensors(window: str, clipboard: str):
        eng.app_sensor = MockActiveWindowSensor(window)
        eng.clip_sensor = MockClipboardSensor(clipboard)

    eng.mock_sensors = mock_sensors
    return eng


def test_neural_engine_debugging_error(engine):
    engine.mock_sensors("Cursor", "Traceback (most recent call last):\n  File 'test.py'")
    context, raw_clip = engine.read_context()
    hyp = engine.infer_intent(context, raw_clip)

    assert hyp is not None
    assert hyp.intent == "debugging_error"
    assert hyp.confidence == "C4"


def test_neural_engine_researching(engine):
    engine.mock_sensors("Google Chrome", "https://github.com/borjamoskv/cortex")
    context, raw_clip = engine.read_context()
    hyp = engine.infer_intent(context, raw_clip)

    assert hyp is not None
    assert hyp.intent == "researching"


def test_neural_engine_planning_linear(engine):
    engine.mock_sensors("Linear", "bug: the button doesn't work")
    context, raw_clip = engine.read_context()
    hyp = engine.infer_intent(context, raw_clip)

    assert hyp is not None
    assert hyp.intent == "planning"


def test_neural_engine_deduplication(engine):
    engine.mock_sensors("Cursor", "Traceback (most recent call last):")
    ctx1, raw1 = engine.read_context()
    hyp1 = engine.infer_intent(ctx1, raw1)
    assert hyp1 is not None

    ctx2, raw2 = engine.read_context()
    hyp2 = engine.infer_intent(ctx2, raw2)
    assert hyp2 is None  # Since it's identical context


def test_neural_engine_unknown_app(engine):
    engine.mock_sensors("unknown", "some copied text")
    context, raw_clip = engine.read_context()
    hyp = engine.infer_intent(context, raw_clip)
    assert hyp is None
