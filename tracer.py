import sys, trace
def main():
    import pytest
    pytest.main(["tests/test_ghost_integration.py", "-s"])
tracer = trace.Trace(count=False, trace=True, ignoredirs=[sys.prefix, sys.exec_prefix])
tracer.run('main()')
