use cortex_rs::babylon::Babylon60;
use cortex_rs::babylon::SCALE;

#[test]
fn test_babylon_basic_arithmetic() {
    let a = Babylon60::new(SCALE); // 1.0
    let b = Babylon60::new(SCALE / 2); // 0.5
    
    // Add
    let c = a.add(&b).unwrap();
    assert_eq!(c.get_value(), SCALE + SCALE / 2); // 1.5
    
    // Sub
    let d = a.sub(&b).unwrap();
    assert_eq!(d.get_value(), SCALE / 2); // 0.5
    
    // Mul
    let e = a.mul(&b).unwrap();
    assert_eq!(e.get_value(), SCALE / 2); // 1.0 * 0.5 = 0.5
    
    // Div
    let f = a.div(&b).unwrap();
    assert_eq!(f.get_value(), 2 * SCALE); // 1.0 / 0.5 = 2.0
}

#[test]
fn test_babylon_overflow() {
    let a = Babylon60::new(i64::MAX);
    let b = Babylon60::new(SCALE); // 1.0

    // Add overflow
    assert!(a.add(&b).is_err());
    
    // Mul overflow check (i64::MAX * 2)
    let c = Babylon60::new(2 * SCALE);
    assert!(a.mul(&c).is_err());
}

#[test]
fn test_babylon_from_float() {
    let a = Babylon60::from_float(1.5);
    assert_eq!(a.get_value(), SCALE + SCALE / 2);
}

#[test]
fn test_babylon_from_int() {
    let a = Babylon60::from_int(2).unwrap();
    assert_eq!(a.get_value(), 2 * SCALE);
}
