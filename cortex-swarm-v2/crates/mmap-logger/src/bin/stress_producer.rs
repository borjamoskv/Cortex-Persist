use mmap_logger::scheduler::SegmentScheduler;
use mmap_logger::EventRecord;
use std::time::Instant;

fn main() {
    let capacity = 50_000;
    let target_events = 200_000; // Limit to 200k to save disk space
    let dir = "/tmp/cortex_stress";
    let _ = std::fs::remove_dir_all(dir); // Clean previous runs
    std::fs::create_dir_all(dir).unwrap();

    let mut current_segment = 0;
    let mut scheduler = SegmentScheduler::new(format!("{}/events_{:03}.mmap", dir, current_segment), capacity).unwrap();
    
    let start = Instant::now();
    for i in 0..target_events {
        let record = EventRecord {
            seq: i as u64, 
            parent_seq: 0,
            hash_env: 0xDEADBEEF,
            agent_id: 42,
            tick: i as u64,
            type_tag: (i % 5) as u8,
            done: 0,
            reserved: [0; 2],
            eval: mmap_logger::EvalVector {
                compile_ok: 1.0,
                test_delta: 0.5,
                regression_risk: 0.1,
                cost: 0.05,
                novelty: 0.9,
                lineage_depth: 2.0,
            },
            obs_offset: 0,
            obs_len: 128,
            action_id: (i % 10) as u32,
            model_version: 1,
            clock_hi: 0,
            clock_lo: i as u64,
        };

        if let Err(_) = scheduler.append(record) {
            // Segment full, rotate
            current_segment += 1;
            scheduler = SegmentScheduler::new(format!("{}/events_{:03}.mmap", dir, current_segment), capacity).unwrap();
            scheduler.append(record).expect("Failed to append after rotation");
        }
    }
    
    scheduler.seal();
    let elapsed = start.elapsed();
    println!("C5-REAL PRODUCER: Inyectados {} eventos en {:?}. Rendimiento: {:.0} ops/sec.", target_events, elapsed, target_events as f64 / elapsed.as_secs_f64());
}
