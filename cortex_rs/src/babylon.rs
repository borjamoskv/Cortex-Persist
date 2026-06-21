use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

pub const SCALE: i64 = 216_000; // 60^3

#[pyclass(module = "cortex_rs")]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Babylon60 {
    value: i64,
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

    pub fn to_float(&self) -> f64 {
        self.value as f64 / SCALE as f64
    }

    pub fn get_value(&self) -> i64 {
        self.value
    }

    pub fn add(&self, other: &Babylon60) -> Babylon60 {
        Babylon60 {
            value: self.value + other.value,
        }
    }

    pub fn sub(&self, other: &Babylon60) -> Babylon60 {
        Babylon60 {
            value: self.value - other.value,
        }
    }

    pub fn mul(&self, other: &Babylon60) -> Babylon60 {
        Babylon60 {
            // Fixed-point multiplication: (a * b) / SCALE
            value: (self.value * other.value) / SCALE,
        }
    }

    pub fn div(&self, other: &Babylon60) -> Babylon60 {
        Babylon60 {
            // Fixed-point division: (a * SCALE) / b
            value: (self.value * SCALE) / other.value,
        }
    }

    fn __add__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        Ok(self.add(other))
    }

    fn __sub__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        Ok(self.sub(other))
    }

    fn __mul__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        Ok(self.mul(other))
    }

    fn __truediv__(&self, other: &Babylon60) -> PyResult<Babylon60> {
        Ok(self.div(other))
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

    #[staticmethod]
    pub fn now() -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let sys_time = SystemTime::now();
        let duration = sys_time.duration_since(UNIX_EPOCH).expect("Time went backwards");
        
        let secs = duration.as_secs() as i64;
        let nanos = duration.subsec_nanos() as i64;
        
        // value = secs * SCALE + (nanos * SCALE) / 1_000_000_000
        let value = secs * SCALE + (nanos * SCALE) / 1_000_000_000;
        Babylon60 { value }
    }
}
