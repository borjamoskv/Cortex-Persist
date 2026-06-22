// FixedPoint60 for Babylon-60 Epistemology
// Replaces F# Cortex.Kernel.FixedPoint

use pyo3::prelude::*;

pub const SCALE: i64 = 216_000;

#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Fixed60 {
    pub raw_value: i64,
}

#[pymethods]
impl Fixed60 {
    #[new]
    pub fn create(integer_part: i64) -> Self {
        Fixed60 {
            raw_value: integer_part * SCALE,
        }
    }

    #[staticmethod]
    pub fn create_dms(deg: i64, min: i64, sec: i64, third: i64) -> Self {
        let sign = if deg < 0 || min < 0 || sec < 0 || third < 0 {
            -1
        } else {
            1
        };
        let abs_deg = deg.abs();
        let abs_min = min.abs();
        let abs_sec = sec.abs();
        let abs_third = third.abs();
        let total = abs_deg * SCALE + abs_min * 3600 + abs_sec * 60 + abs_third;
        Fixed60 {
            raw_value: sign * total,
        }
    }

    #[staticmethod]
    pub fn add(a: &Fixed60, b: &Fixed60) -> Self {
        Fixed60 {
            raw_value: a.raw_value + b.raw_value,
        }
    }

    #[staticmethod]
    pub fn sub(a: &Fixed60, b: &Fixed60) -> Self {
        Fixed60 {
            raw_value: a.raw_value - b.raw_value,
        }
    }

    #[staticmethod]
    pub fn mul(a: &Fixed60, b: &Fixed60) -> Self {
        let big_a = a.raw_value as i128;
        let big_b = b.raw_value as i128;
        let big_s = SCALE as i128;
        let res = (big_a * big_b) / big_s;
        Fixed60 {
            raw_value: res as i64,
        }
    }

    #[staticmethod]
    pub fn div(a: &Fixed60, b: &Fixed60) -> Self {
        let big_a = a.raw_value as i128;
        let big_b = b.raw_value as i128;
        let big_s = SCALE as i128;
        if big_b == 0 {
            return Fixed60 { raw_value: 0 };
        }
        let res = (big_a * big_s) / big_b;
        Fixed60 {
            raw_value: res as i64,
        }
    }

    pub fn to_deg_min_sec_third(&self) -> (i64, i64, i64, i64) {
        let sign = if self.raw_value < 0 { -1 } else { 1 };
        let abs_val = self.raw_value.abs();
        let deg = abs_val / SCALE;
        let rem1 = abs_val % SCALE;
        let min = rem1 / 3600;
        let rem2 = rem1 % 3600;
        let sec = rem2 / 60;
        let third = rem2 % 60;
        (sign * deg, min, sec, third)
    }

    pub fn to_float(&self) -> f64 {
        self.raw_value as f64 / SCALE as f64
    }

    #[staticmethod]
    pub fn from_float(x: f64) -> Self {
        Fixed60 {
            raw_value: (x * SCALE as f64).round() as i64,
        }
    }
}
