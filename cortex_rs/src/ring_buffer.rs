//! ZeroCopyRingBuffer — L1 cache-aligned lock-free ring buffer (Issue #411).
//!
//! Uses `#[repr(align(64))]` on slot elements to align each entry to a CPU
//! L1 cache line (64 bytes on x86-64 and ARM64). This eliminates false sharing
//! between producer and consumer threads operating on adjacent slots under
//! high-contention conditions in the LEGION-10k swarm dispatch path.
//!
//! # Design
//!
//! - `AlignedSlot<T>` wraps any `T` with 64-byte alignment.
//! - `ZeroCopyRingBuffer<T>` uses a `Box<[AlignedSlot<T>]>` as backing store.
//! - Capacity is rounded up to the next power of two so the index mask
//!   `(capacity - 1)` can replace modulo operations.
//! - Exposed to Python via pyo3 as a `u64` payload ring buffer.
//!
//! # Cross-platform compatibility
//!
//! `#[repr(align(64))]` is supported on all Tier 1 Rust targets. The alignment
//! value matches the cache line size on x86-64, ARM64, and RISC-V.

use std::sync::atomic::{AtomicUsize, Ordering};

use pyo3::prelude::*;

// ---------------------------------------------------------------------------
// AlignedSlot: cache-line-aligned wrapper
// ---------------------------------------------------------------------------

/// A single ring buffer slot padded and aligned to one CPU cache line (64 B).
///
/// `#[repr(align(64))]` guarantees that each slot starts on a 64-byte boundary,
/// preventing false sharing between adjacent slots accessed by different CPUs.
#[repr(align(64))]
#[derive(Clone, Debug, Default)]
pub struct AlignedSlot<T: Clone + Default> {
    /// The payload stored in this slot.
    pub value: T,
    // Padding to fill the remainder of the 64-byte cache line when T is small.
    // This is implicit: `repr(align(64))` ensures the *struct* is 64-byte
    // aligned; the compiler inserts any necessary tail-padding automatically.
}

impl<T: Clone + Default> AlignedSlot<T> {
    #[inline]
    pub fn new(value: T) -> Self {
        Self { value }
    }
}

// ---------------------------------------------------------------------------
// ZeroCopyRingBuffer
// ---------------------------------------------------------------------------

/// A lock-free, cache-line-aligned single-producer/single-consumer ring buffer.
///
/// Capacity is always a power of two so index arithmetic can use bitwise AND
/// instead of modulo, which is measurably faster under high throughput.
///
/// # Thread safety
///
/// `head` and `tail` are `AtomicUsize` with `Release`/`Acquire` ordering,
/// suitable for one producer and one consumer thread (SPSC). Multi-producer or
/// multi-consumer use requires additional synchronisation.
pub struct ZeroCopyRingBuffer<T: Clone + Default> {
    slots: Box<[AlignedSlot<T>]>,
    capacity: usize,
    mask: usize,
    head: AtomicUsize, // next write position (producer)
    tail: AtomicUsize, // next read position  (consumer)
}

impl<T: Clone + Default> ZeroCopyRingBuffer<T> {
    /// Create a new ring buffer.
    ///
    /// `capacity` is rounded up to the next power of two. The minimum
    /// effective capacity is 2.
    pub fn new(capacity: usize) -> Self {
        let cap = capacity.next_power_of_two().max(2);
        let slots: Box<[AlignedSlot<T>]> = (0..cap)
            .map(|_| AlignedSlot::default())
            .collect::<Vec<_>>()
            .into_boxed_slice();

        // Verify alignment at runtime (debug builds only).
        debug_assert_eq!(
            slots.as_ptr() as usize % 64,
            0,
            "Ring buffer slots must be 64-byte aligned"
        );
        debug_assert_eq!(
            std::mem::align_of::<AlignedSlot<T>>(),
            64,
            "AlignedSlot alignment must be 64"
        );

        Self {
            slots,
            capacity: cap,
            mask: cap - 1,
            head: AtomicUsize::new(0),
            tail: AtomicUsize::new(0),
        }
    }

    /// Returns the (power-of-two) capacity of the ring buffer.
    #[inline]
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Returns the number of elements currently in the buffer.
    #[inline]
    pub fn len(&self) -> usize {
        let head = self.head.load(Ordering::Acquire);
        let tail = self.tail.load(Ordering::Acquire);
        head.wrapping_sub(tail)
    }

    /// Returns `true` if the buffer contains no elements.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Returns `true` if the buffer is full.
    #[inline]
    pub fn is_full(&self) -> bool {
        self.len() == self.capacity
    }

    /// Push a value into the ring buffer.
    ///
    /// Returns `Ok(())` on success or `Err(value)` if the buffer is full.
    pub fn push(&self, value: T) -> Result<(), T> {
        let head = self.head.load(Ordering::Relaxed);
        let tail = self.tail.load(Ordering::Acquire);
        if head.wrapping_sub(tail) == self.capacity {
            return Err(value); // buffer full
        }
        // SAFETY: head & mask is always in [0, capacity).
        unsafe {
            let slot = &self.slots[head & self.mask] as *const AlignedSlot<T> as *mut AlignedSlot<T>;
            (*slot).value = value;
        }
        self.head.store(head.wrapping_add(1), Ordering::Release);
        Ok(())
    }

    /// Pop a value from the ring buffer.
    ///
    /// Returns `Some(value)` if available, `None` if the buffer is empty.
    pub fn pop(&self) -> Option<T> {
        let tail = self.tail.load(Ordering::Relaxed);
        let head = self.head.load(Ordering::Acquire);
        if tail == head {
            return None; // buffer empty
        }
        // SAFETY: tail & mask is always in [0, capacity).
        let value = unsafe {
            let slot = &self.slots[tail & self.mask];
            slot.value.clone()
        };
        self.tail.store(tail.wrapping_add(1), Ordering::Release);
        Some(value)
    }
}

// SAFETY: ZeroCopyRingBuffer uses AtomicUsize for head/tail and only mutates
// slots through raw pointer writes that are sequenced by the atomics.
// This makes it safe to share across threads as SPSC.
unsafe impl<T: Clone + Default + Send> Send for ZeroCopyRingBuffer<T> {}
unsafe impl<T: Clone + Default + Send> Sync for ZeroCopyRingBuffer<T> {}

// ---------------------------------------------------------------------------
// pyo3 Python bindings: ZeroCopyRingBuffer<u64>
// ---------------------------------------------------------------------------

/// Python-visible ring buffer with u64 payloads.
///
/// Exposed as `cortex_rs.ZeroCopyRingBuffer`. Capacity is always rounded up
/// to the next power of two by the underlying Rust implementation.
#[pyclass(name = "ZeroCopyRingBuffer")]
pub struct PyZeroCopyRingBuffer {
    inner: ZeroCopyRingBuffer<u64>,
}

#[pymethods]
impl PyZeroCopyRingBuffer {
    /// Create a new ring buffer with at least `capacity` slots.
    #[new]
    pub fn new(capacity: usize) -> Self {
        Self {
            inner: ZeroCopyRingBuffer::new(capacity),
        }
    }

    /// Push a u64 value. Returns True on success, False if buffer is full.
    pub fn push(&self, value: u64) -> bool {
        self.inner.push(value).is_ok()
    }

    /// Pop a u64 value. Returns None if buffer is empty.
    pub fn pop(&self) -> Option<u64> {
        self.inner.pop()
    }

    /// Current number of elements in the buffer.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// True if the buffer is empty.
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// True if the buffer is full.
    pub fn is_full(&self) -> bool {
        self.inner.is_full()
    }

    /// Effective capacity (next power of two >= requested capacity).
    pub fn capacity(&self) -> usize {
        self.inner.capacity()
    }

    pub fn __repr__(&self) -> String {
        format!(
            "ZeroCopyRingBuffer(capacity={}, len={}, align=64)",
            self.inner.capacity(),
            self.inner.len(),
        )
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_alignment() {
        assert_eq!(std::mem::align_of::<AlignedSlot<u64>>(), 64);
        assert_eq!(std::mem::align_of::<AlignedSlot<u8>>(), 64);
    }

    #[test]
    fn test_capacity_rounded_to_power_of_two() {
        let rb = ZeroCopyRingBuffer::<u64>::new(100);
        assert_eq!(rb.capacity(), 128);

        let rb2 = ZeroCopyRingBuffer::<u64>::new(1);
        assert_eq!(rb2.capacity(), 2);

        let rb3 = ZeroCopyRingBuffer::<u64>::new(256);
        assert_eq!(rb3.capacity(), 256);
    }

    #[test]
    fn test_push_pop_roundtrip() {
        let rb = ZeroCopyRingBuffer::<u64>::new(4);
        assert!(rb.push(42).is_ok());
        assert!(rb.push(99).is_ok());
        assert_eq!(rb.pop(), Some(42));
        assert_eq!(rb.pop(), Some(99));
        assert_eq!(rb.pop(), None);
    }

    #[test]
    fn test_full_and_empty() {
        let rb = ZeroCopyRingBuffer::<u64>::new(2);
        assert!(rb.is_empty());
        assert!(rb.push(1).is_ok());
        assert!(rb.push(2).is_ok());
        assert!(rb.is_full());
        assert_eq!(rb.push(3), Err(3));
        rb.pop();
        assert!(!rb.is_full());
    }

    #[test]
    fn test_zero_performance_regression_check() {
        // Verifies that the push/pop cycle completes without panic.
        // Actual throughput benchmarks live in benchmarks/.
        let rb = ZeroCopyRingBuffer::<u64>::new(1024);
        for i in 0..1024_u64 {
            assert!(rb.push(i).is_ok());
        }
        for i in 0..1024_u64 {
            assert_eq!(rb.pop(), Some(i));
        }
    }
}
