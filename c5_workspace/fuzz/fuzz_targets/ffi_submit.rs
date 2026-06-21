#![no_main]

use libfuzzer_sys::fuzz_target;
use cortex_ffi::BoundaryKernel;

fuzz_target!(|data: &[u8]| {
    let mut kernel = BoundaryKernel::new();
    let input = String::from_utf8_lossy(data);
    let _ = kernel.submit_ir(&input);
});
