use criterion::{criterion_group, criterion_main, Criterion};
use std::hint::black_box;
use cortex_rs::vector_vault::VectorVault;

fn generate_random_f32(i: usize) -> f32 {
    (i as f32) * 0.01
}

fn benchmark_encrypt(c: &mut Criterion) {
    let key = VectorVault::generate_key();
    let vault = VectorVault::new(&key, 1024);
    
    let vec_1024: Vec<f32> = (0..1024).map(|i| generate_random_f32(i)).collect();
    
    c.bench_function("vault encrypt 1024d", |b| b.iter(|| {
        vault.encrypt(black_box(&vec_1024)).unwrap()
    }));
}

fn benchmark_decrypt(c: &mut Criterion) {
    let key = VectorVault::generate_key();
    let vault = VectorVault::new(&key, 1024);
    
    let vec_1024: Vec<f32> = (0..1024).map(|i| generate_random_f32(i)).collect();
    let encrypted = vault.encrypt(&vec_1024).unwrap();
    
    c.bench_function("vault decrypt 1024d", |b| b.iter(|| {
        vault.decrypt(black_box(&encrypted)).unwrap()
    }));
}

fn benchmark_search_encrypted(c: &mut Criterion) {
    let key = VectorVault::generate_key();
    let vault = VectorVault::new(&key, 1024);
    
    let query: Vec<f32> = (0..1024).map(|i| generate_random_f32(i)).collect();
    
    let db_size = 100; // Small batch to prevent timeout
    let mut db = Vec::with_capacity(db_size);
    for _ in 0..db_size {
        let v: Vec<f32> = (0..1024).map(|i| generate_random_f32(i)).collect();
        db.push(vault.encrypt(&v).unwrap());
    }
    
    c.bench_function("vault search 100 x 1024d", |b| b.iter(|| {
        vault.search_encrypted(black_box(&query), black_box(&db), 10, 0.5).unwrap()
    }));
}

criterion_group!(benches, benchmark_encrypt, benchmark_decrypt, benchmark_search_encrypted);
criterion_main!(benches);
