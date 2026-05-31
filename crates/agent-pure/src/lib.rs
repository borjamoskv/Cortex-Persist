#[no_mangle]
pub extern "C" fn process_friction(friction: f64) -> f64 {
    // Pure thermodynamic reduction function
    // For every unit of friction, entropy drops if we can assimilate it.
    let assimilation_rate = 0.85;
    let entropy_delta = -(friction * assimilation_rate);
    entropy_delta
}
