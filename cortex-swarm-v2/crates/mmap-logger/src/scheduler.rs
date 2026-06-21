use memmap2::{MmapMut, MmapOptions};
use std::fs::OpenOptions;
use std::path::Path;
use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};

use crate::{EventRecord, SegmentHeader};

/// C5-REAL Segment Scheduler (Plano Caliente)
/// Escribe eventos de manera append-only en un bloque MMAP sellable.
pub struct SegmentScheduler {
    mmap: MmapMut,
    capacity: u32,
    pub global_seq: AtomicU64,
}

impl SegmentScheduler {
    pub fn new<P: AsRef<Path>>(path: P, capacity: u32) -> std::io::Result<Self> {
        let file_size = std::mem::size_of::<SegmentHeader>() as u64 
            + (capacity as u64 * std::mem::size_of::<EventRecord>() as u64);

        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(path)?;

        file.set_len(file_size)?;

        let mut mmap = unsafe { MmapOptions::new().map_mut(&file)? };

        // Initialize header if empty
        let header = unsafe { &mut *(mmap.as_mut_ptr() as *mut SegmentHeader) };
        if header.magic == 0 {
            header.magic = 0xC5C5_0000_0000_0000;
            header.version = 1;
            header.sealed = 0;
            header.record_count = 0;
            header.capacity = capacity;
        }

        Ok(Self {
            mmap,
            capacity,
            global_seq: AtomicU64::new(0),
        })
    }

    pub fn append(&mut self, mut record: EventRecord) -> Result<(), &'static str> {
        let header = unsafe { &mut *(self.mmap.as_mut_ptr() as *mut SegmentHeader) };

        if header.sealed == 1 {
            return Err("SAGA-1: Segmento sellado, colapso denegado.");
        }

        if header.record_count >= self.capacity {
            self.seal();
            return Err("SAGA-1: Capacidad máxima alcanzada. Segmento sellado.");
        }

        // Assign monotonic sequence
        record.seq = self.global_seq.fetch_add(1, Ordering::SeqCst);

        // Write record
        let record_offset = std::mem::size_of::<SegmentHeader>() 
            + (header.record_count as usize * std::mem::size_of::<EventRecord>());
            
        unsafe {
            let dest = self.mmap.as_mut_ptr().add(record_offset) as *mut EventRecord;
            std::ptr::write(dest, record);
        }

        header.record_count += 1;
        
        Ok(())
    }

    pub fn seal(&mut self) {
        let header = unsafe { &mut *(self.mmap.as_mut_ptr() as *mut SegmentHeader) };
        header.sealed = 1;
        // header.checksum = compute_checksum(...);
        self.mmap.flush().unwrap();
    }
}
