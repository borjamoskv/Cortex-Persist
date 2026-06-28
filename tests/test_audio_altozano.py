import os
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

try:
    from cortex.extensions.audio.altozano import AltozanoAnalyzer
except ImportError:
    pass

@pytest.fixture
def mock_audio_file(tmp_path):
    """Generates a pure 440Hz Sine Wave (A4 note) and saves to a temp WAV."""
    path = tmp_path / "test_A4.wav"
    sr = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # 440Hz is A
    y = np.sin(2 * np.pi * 440.0 * t)
    
    sf.write(path, y, sr)
    return path

def test_altozano_deconstruct(mock_audio_file):
    try:
        import librosa
    except ImportError:
        pytest.skip("librosa not installed, skipping Altozano tests")
        
    analyzer = AltozanoAnalyzer()
    
    report = analyzer.deconstruct_track(mock_audio_file)
    
    assert report["track"] == "test_A4.wav"
    assert report["sample_rate_hz"] == 22050
    assert report["duration_sec"] == 1.0
    
    # 440Hz is an 'A'. The dominant note should be 'A'.
    # Sometimes it might pick up harmonics, but A should definitely be in the top notes.
    assert "A" in report["dominant_pitch_classes"]
    
    assert "La fundamental inferida es" in report["structural_analysis"]
