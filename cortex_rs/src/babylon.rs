use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyZeroDivisionError, PyOverflowError};
use serde::{Deserialize, Serialize};
use std::hash::{Hash, Hasher};

pub const SCALE: i64 = 216_000; // 60^3

#[pyclass(module = "cortex_rs")]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Babylon60 {
    value: i64,
}

impl Hash for Babylon60 {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.value.hash(state);
    }
}

#[pymethods]
impl Babylon60 {
    #[new]
    pub fn new(value: i64) -> Self {
        Babylon60 { value }
    }

    #[staticmethod]
    pub fn from_float(f: f64) -> Self {
        Babylon60 {
            value: (f * SCALE as f64).round() as i64,
        }
    }

    #[staticmethod]
    pub fn from_int(i: i64) -> PyResult<Self> {
        let value = i.checked_mul(SCALE).ok_or_else(|| PyOverflowError::new_err("Integer overflow"))?;
        Ok(Babylon60 { value })
    }

    pub fn to_float(&self) -> f64 {
        self.value as f64 / SCALE as f64
    }

    pub fn get_value(&self) -> i64 {
        self.value
    }

    pub fn add(&self, other: &Babylon60) -> PyResult<Babylon60> {
        let value = self.value.checked_add(other.value).ok_or_else(|| PyOverflowError::new_err("Addition overflow"))?;
        Ok(Babylon60 { value })
    }

    pub fn sub(&self, other: &Babylon60) -> PyResult<Babylon60> {
        let value = self.value.checked_sub(other.value).ok_or_else(|| PyOverflowError::new_err("Subtraction overflow"))?;
        Ok(Babylon60 { value })
    }

    pub fn mul(&self, other: &Babylon60) -> PyResult<Babylon60> {
        // Use i128 for fixed-point multiplication to prevent overflow: (a * b) / SCALE
        let val_128 = (self.value as i128) * (other.value as i128) / (SCALE as i128);
        if val_128 > i64::MAX as i128 || val_128 < i64::MIN as i128 {
            return Err(PyOverflowError::new_err("Multiplication overflow"));
        }
        Ok(Babylon60 { value: val_128 as i64 })
    }

    pub fn div(&self, other: &Babylon60) -> PyResult<Babylon60> {
        if other.value == 0 {
            return Err(PyZeroDivisionError::new_err("Division by zero in Babylon60"));
        }
        // Use i128 for fixed-point division: (a * SCALE) / b
        let val_128 = (self.value as i128) * (SCALE as i128) / (other.value as i128);
        if val_128 > i64::MAX as i128 || val_128 < i64::MIN as i128 {
            return Err(PyOverflowError::new_err("Division overflow"));
        }
        Ok(Babylon60 { value: val_128 as i64 })
    }

    fn __add__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        self.add(other)
    }

    fn __sub__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        self.sub(other)
    }

    fn __mul__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        self.mul(other)
    }

    fn __truediv__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        self.div(other)
    }

    fn __eq__(&self, other: &Babylon60) -> bool {
        self.value == other.value
    }

    fn __lt__(&self, other: &Babylon60) -> bool {
        self.value < other.value
    }

    fn __le__(&self, other: &Babylon60) -> bool {
        self.value <= other.value
    }

    fn __gt__(&self, other: &Babylon60) -> bool {
        self.value > other.value
    }

    fn __ge__(&self, other: &Babylon60) -> bool {
        self.value >= other.value
    }

    fn __str__(&self) -> String {
        format!("{}", self.to_float())
    }

    fn __repr__(&self) -> String {
        format!("Babylon60(value={})", self.value)
    }

    fn __float__(&self) -> f64 {
        self.to_float()
    }

    fn __int__(&self) -> i64 {
        self.value / SCALE
    }

    fn __hash__(&self) -> u64 {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.hash(&mut hasher);
        hasher.finish()
    }

    #[staticmethod]
    pub fn now() -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let sys_time = SystemTime::now();
        let duration = sys_time.duration_since(UNIX_EPOCH).expect("Time went backwards");
        
        let secs = duration.as_secs() as i64;
        let nanos = duration.subsec_nanos() as i64;
        
        // value = secs * SCALE + (nanos * SCALE) / 1_000_000_000
        let value = secs.saturating_mul(SCALE).saturating_add((nanos as i128 * SCALE as i128 / 1_000_000_000) as i64);
        Babylon60 { value }
    }
}
