use criterion::{black_box, criterion_group, criterion_main, Criterion};
use cortex_rs::vector_vault::VectorVault;
use rand::RngCore;

fn generate_random_f32() -> f32 {
    let mut rng = rand::rngs::OsRng;
    let mut bytes = [0u8; 4];
    rng.fill_bytes(&mut bytes);
    f32::from_le_bytes(bytes)
}

fn benchmark_encrypt(c: &mut Criterion) {
    let key = VectorVault::generate_key();
    let vault = VectorVault::new(&key);
    
    let vec_1024: Vec<f32> = (0..1024).map(|_| generate_random_f32()).collect();
    
    c.bench_function("vault encrypt 1024d", |b| b.iter(|| {
        vault.encrypt(black_box(&vec_1024)).unwrap()
    }));
}

fn benchmark_decrypt(c: &mut Criterion) {
    let key = VectorVault::generate_key();
    let vault = VectorVault::new(&key);
    
    let vec_1024: Vec<f32> = (0..1024).map(|_| generate_random_f32()).collect();
    let encrypted = vault.encrypt(&vec_1024).unwrap();
    
    c.bench_function("vault decrypt 1024d", |b| b.iter(|| {
        vault.decrypt(black_box(&encrypted)).unwrap()
    }));
}

fn benchmark_search_encrypted(c: &mut Criterion) {
    let key = VectorVault::generate_key();
    let vault = VectorVault::new(&key);
    
    let query: Vec<f32> = (0..1024).map(|_| generate_random_f32()).collect();
    
    let db_size = 100; // Small batch to prevent timeout
    let mut db = Vec::with_capacity(db_size);
    for _ in 0..db_size {
        let v: Vec<f32> = (0..1024).map(|_| generate_random_f32()).collect();
        db.push(vault.encrypt(&v).unwrap());
    }
    
    c.bench_function("vault search 100 x 1024d", |b| b.iter(|| {
        vault.search_encrypted(black_box(&query), black_box(&db), 10, 0.5).unwrap()
    }));
}

criterion_group!(benches, benchmark_encrypt, benchmark_decrypt, benchmark_search_encrypted);
criterion_main!(benches);
