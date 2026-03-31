import pytest


class DummyRequiredGuard:
    required = True
    name = "dummy_required"

    def evaluate(self, context):
        raise RuntimeError("boom")


def run_pipeline(guards):
    for g in guards:
        try:
            g.evaluate({})
        except Exception:
            if getattr(g, "required", False):
                raise


def test_required_guard_exception_aborts_write():
    guards = [DummyRequiredGuard()]

    with pytest.raises(RuntimeError):
        run_pipeline(guards)
