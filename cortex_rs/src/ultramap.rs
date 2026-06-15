use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3::types::PyDict;
use std::fs::OpenOptions;
use std::sync::{Arc, Mutex};
use memmap2::{MmapMut, MmapOptions};
use sha2::{Sha256, Digest};
use std::panic;

fn strip_trailing_nulls(bytes: &[u8]) -> &[u8] {
    let mut len = bytes.len();
    while len > 0 && bytes[len - 1] == 0 {
        len -= 1;
    }
    &bytes[..len]
}

/// A thread-safe spatial-temporal swarm topology engine (memory-mapped) to bypass GIL.
#[pyclass]
pub struct UltramapSubstrate {
    mmap: Arc<Mutex<MmapMut>>,
    capacity: usize,
    node_size: usize,
}

#[pymethods]
impl UltramapSubstrate {
    #[new]
    #[pyo3(signature = (bin_path, capacity=None))]
    pub fn new(bin_path: &str, capacity: Option<usize>) -> PyResult<Self> {
        let capacity = capacity.unwrap_or(10000);
        let node_size = 128; // UESS v2: 128 bytes node size
        let tensor_size = capacity * node_size;

        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(bin_path)
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to open ultramap file: {}", e)))?;

        if file.metadata().map_err(|e| PyRuntimeError::new_err(format!("Failed to read metadata: {}", e)))?.len() < tensor_size as u64 {
            file.set_len(tensor_size as u64)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to allocate ultramap file: {}", e)))?;
        }

        let mmap = unsafe {
            MmapOptions::new()
                .len(tensor_size)
                .map_mut(&file)
                .map_err(|e| PyRuntimeError::new_err(format!("Mmap failed: {}", e)))?
        };

        Ok(UltramapSubstrate {
            mmap: Arc::new(Mutex::new(mmap)),
            capacity,
            node_size,
        })
    }

    pub fn update_agent_position(&self, agent_idx: usize, x: f64, y: f64, z: f64, target: &str, entropy: f64) -> PyResult<bool> {
        if agent_idx >= self.capacity {
            return Ok(false);
        }

        let mut mmap = self.mmap.lock().unwrap();
        let offset = agent_idx * self.node_size;
        let write_result = panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            unsafe {
                std::slice::from_raw_parts_mut(mmap.as_mut_ptr(), self.capacity * self.node_size)
            }
        }));
        let buffer: &mut [u8] = match write_result {
            Ok(buf) => buf,
            Err(_) => return Err(PyRuntimeError::new_err(
                "[ultramap] SIGBUS: página mmap invalidada por macOS en escritura — archivo ultramap.bin truncado o purgado"
            )),
        };

        // Pack x, y, z
        buffer[offset..offset + 8].copy_from_slice(&x.to_ne_bytes());
        buffer[offset + 8..offset + 16].copy_from_slice(&y.to_ne_bytes());
        buffer[offset + 16..offset + 24].copy_from_slice(&z.to_ne_bytes());

        // Target (64 bytes)
        let mut target_bytes = [0u8; 64];
        let len = target.len().min(64);
        target_bytes[..len].copy_from_slice(&target.as_bytes()[..len]);
        buffer[offset + 24..offset + 88].copy_from_slice(&target_bytes);

        // Entropy
        buffer[offset + 88..offset + 96].copy_from_slice(&entropy.to_ne_bytes());

        mmap.flush()
            .map_err(|e| PyRuntimeError::new_err(format!("[ultramap] msync failed: {}", e)))?;

        Ok(true)
    }

    pub fn calculate_exergy_distance(&self, agent_idx: usize, target_hash: &str) -> PyResult<f64> {
        if agent_idx >= self.capacity {
            return Err(PyRuntimeError::new_err("Agent Index Out of Bounds"));
        }

        let mmap = self.mmap.lock().unwrap();
        let offset = agent_idx * self.node_size;
        let read_result = panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            unsafe {
                std::slice::from_raw_parts(mmap.as_ptr(), self.capacity * self.node_size)
            }
        }));
        let buffer: &[u8] = match read_result {
            Ok(buf) => buf,
            Err(_) => return Err(PyRuntimeError::new_err(
                "[ultramap] SIGBUS: página mmap invalidada por macOS en lectura — archivo ultramap.bin truncado o purgado"
            )),
        };

        let mut x_bytes = [0u8; 8];
        x_bytes.copy_from_slice(&buffer[offset..offset + 8]);
        let x = f64::from_ne_bytes(x_bytes);

        let mut y_bytes = [0u8; 8];
        y_bytes.copy_from_slice(&buffer[offset + 8..offset + 16]);
        let y = f64::from_ne_bytes(y_bytes);

        let mut z_bytes = [0u8; 8];
        z_bytes.copy_from_slice(&buffer[offset + 16..offset + 24]);
        let z = f64::from_ne_bytes(z_bytes);

        let mut entropy_bytes = [0u8; 8];
        entropy_bytes.copy_from_slice(&buffer[offset + 88..offset + 96]);
        let current_entropy = f64::from_ne_bytes(entropy_bytes);

        // Hash to deterministic coordinates
        let mut hasher = Sha256::new();
        hasher.update(target_hash.as_bytes());
        let hash_result = hasher.finalize();

        let mut target_int: u64 = 0;
        for i in 0..8 {
            target_int = (target_int << 8) | hash_result[i] as u64;
        }

        let tx = (target_int % 1000) as f64 / 10.0;
        let ty = ((target_int >> 4) % 1000) as f64 / 10.0;
        let tz = ((target_int >> 8) % 1000) as f64 / 10.0;

        let distance = ((tx - x).powi(2) + (ty - y).powi(2) + (tz - z).powi(2)).sqrt();
        let joules = distance * (1.0 / (current_entropy + 0.001));

        Ok(joules)
    }

    pub fn get_agent_state<'py>(&self, py: Python<'py>, agent_idx: usize) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        if agent_idx >= self.capacity {
            return Ok(dict);
        }

        let mmap = self.mmap.lock().unwrap();
        let offset = agent_idx * self.node_size;
        let read_result = panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            unsafe {
                std::slice::from_raw_parts(mmap.as_ptr(), self.capacity * self.node_size)
            }
        }));
        let buffer: &[u8] = match read_result {
            Ok(buf) => buf,
            Err(_) => return Err(PyRuntimeError::new_err(
                "[ultramap] SIGBUS: página mmap invalidada por macOS en lectura — archivo ultramap.bin truncado o purgado"
            )),
        };

        let mut x_bytes = [0u8; 8];
        x_bytes.copy_from_slice(&buffer[offset..offset + 8]);
        let x = f64::from_ne_bytes(x_bytes);

        let mut y_bytes = [0u8; 8];
        y_bytes.copy_from_slice(&buffer[offset + 8..offset + 16]);
        let y = f64::from_ne_bytes(y_bytes);

        let mut z_bytes = [0u8; 8];
        z_bytes.copy_from_slice(&buffer[offset + 16..offset + 24]);
        let z = f64::from_ne_bytes(z_bytes);

        let target_raw = &buffer[offset + 24..offset + 88];
        let target_len_bytes = strip_trailing_nulls(target_raw);
        let target = String::from_utf8_lossy(target_len_bytes).into_owned();

        let mut entropy_bytes = [0u8; 8];
        entropy_bytes.copy_from_slice(&buffer[offset + 88..offset + 96]);
        let entropy = f64::from_ne_bytes(entropy_bytes);

        // UESS v2: Control Vector (queue_depth, error_rate, causal_entropy, cpu_load) at [96:128]
        let mut qd_bytes = [0u8; 8];
        qd_bytes.copy_from_slice(&buffer[offset + 96..offset + 104]);
        let queue_depth = f64::from_ne_bytes(qd_bytes);

        let mut er_bytes = [0u8; 8];
        er_bytes.copy_from_slice(&buffer[offset + 104..offset + 112]);
        let error_rate = f64::from_ne_bytes(er_bytes);

        let mut ce_bytes = [0u8; 8];
        ce_bytes.copy_from_slice(&buffer[offset + 112..offset + 120]);
        let causal_entropy = f64::from_ne_bytes(ce_bytes);

        let mut cl_bytes = [0u8; 8];
        cl_bytes.copy_from_slice(&buffer[offset + 120..offset + 128]);
        let cpu_load = f64::from_ne_bytes(cl_bytes);

        dict.set_item("x", x)?;
        dict.set_item("y", y)?;
        dict.set_item("z", z)?;
        dict.set_item("target", target)?;
        dict.set_item("entropy", entropy)?;
        dict.set_item("queue_depth", queue_depth)?;
        dict.set_item("error_rate", error_rate)?;
        dict.set_item("causal_entropy", causal_entropy)?;
        dict.set_item("cpu_load", cpu_load)?;

        Ok(dict)
    }

    pub fn update_control_vector(&self, agent_idx: usize, queue_depth: f64, error_rate: f64, causal_entropy: f64, cpu_load: f64) -> PyResult<bool> {
        if agent_idx >= self.capacity {
            return Ok(false);
        }

        let mut mmap = self.mmap.lock().unwrap();
        let offset = agent_idx * self.node_size;
        let write_result = panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            unsafe {
                std::slice::from_raw_parts_mut(mmap.as_mut_ptr(), self.capacity * self.node_size)
            }
        }));
        let buffer: &mut [u8] = match write_result {
            Ok(buf) => buf,
            Err(_) => return Err(PyRuntimeError::new_err(
                "[ultramap] SIGBUS: página mmap invalidada por macOS en escritura — archivo ultramap.bin truncado o purgado"
            )),
        };

        // Extract x, y, z to verify initialization
        let mut x_bytes = [0u8; 8];
        x_bytes.copy_from_slice(&buffer[offset..offset + 8]);
        let x = f64::from_ne_bytes(x_bytes);

        let mut y_bytes = [0u8; 8];
        y_bytes.copy_from_slice(&buffer[offset + 8..offset + 16]);
        let y = f64::from_ne_bytes(y_bytes);

        let mut z_bytes = [0u8; 8];
        z_bytes.copy_from_slice(&buffer[offset + 16..offset + 24]);
        let z = f64::from_ne_bytes(z_bytes);

        if x == 0.0 && y == 0.0 && z == 0.0 {
            return Ok(false);
        }

        // Pack Control Vector fields at [96:128]
        buffer[offset + 96..offset + 104].copy_from_slice(&queue_depth.to_ne_bytes());
        buffer[offset + 104..offset + 112].copy_from_slice(&error_rate.to_ne_bytes());
        buffer[offset + 112..offset + 120].copy_from_slice(&causal_entropy.to_ne_bytes());
        buffer[offset + 120..offset + 128].copy_from_slice(&cpu_load.to_ne_bytes());

        mmap.flush()
            .map_err(|e| PyRuntimeError::new_err(format!("[ultramap] msync failed: {}", e)))?;

        Ok(true)
    }

    pub fn get_address(&self) -> usize {
        let mmap = self.mmap.lock().unwrap();
        mmap.as_ptr() as usize
    }
}
