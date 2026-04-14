from pathlib import Path


def test_compaction_runner_uses_sovereign_run() -> None:
    runner_path = (
        Path(__file__).resolve().parents[1]
        / "cortex"
        / "extensions"
        / "daemon"
        / "sidecar"
        / "compaction_monitor"
        / "runner.py"
    )
    source = runner_path.read_text(encoding="utf-8")

    assert "sovereign_run(main())" in source
    assert "set_event_loop_policy" not in source
    assert "EventLoopPolicy" not in source
