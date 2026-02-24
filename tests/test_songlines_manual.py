import os
import shutil
import tempfile
from pathlib import Path
from cortex.songlines.emitter import ResonanceEmitter
from cortex.songlines.sensor import TopographicSensor
from cortex.songlines.economy import ThermalEconomy
from cortex.songlines.decay import DecayEngine

def test_songline_cycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        emitter = ResonanceEmitter()
        sensor = TopographicSensor()
        economy = ThermalEconomy(sensor=sensor)
        
        # 1. Embed ghost
        emitter.embed_ghost(test_file, "Implement the main loop", project="test_proj")
        
        # 2. Sensor detects it
        ghosts = sensor.scan_field(tmp_path)
        assert len(ghosts) == 1
        assert ghosts[0]['intent'] == "Implement the main loop"
        assert ghosts[0]['project'] == "test_proj"
        assert 0.99 <= ghosts[0]['strength'] <= 1.0
        
        # 3. Economy tracks it
        status = economy.check_entropy(tmp_path)
        assert status['count'] == 1
        assert not status['is_saturated']
        
        print("Songline Cycle Verified: Embed -> Scan -> Economy")

if __name__ == "__main__":
    test_songline_cycle()
