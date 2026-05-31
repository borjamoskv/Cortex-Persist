import cortex_rs

original_init = cortex_rs.ZeroCopyRingBuffer.__init__


def mocked_init(self, capacity=100):
    original_init(self, capacity=capacity)


cortex_rs.ZeroCopyRingBuffer.__init__ = mocked_init
try:
    cortex_rs.ZeroCopyRingBuffer(capacity=100)
except Exception as e:
    print(e)
