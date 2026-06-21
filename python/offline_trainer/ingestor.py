import mmap
import ctypes
import os

class SegmentHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint64),
        ("version", ctypes.c_uint32),
        ("sealed", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8 * 3),
        ("segment_id", ctypes.c_uint64),
        ("start_seq", ctypes.c_uint64),
        ("end_seq", ctypes.c_uint64),
        ("record_count", ctypes.c_uint32),
        ("capacity", ctypes.c_uint32),
        ("checksum", ctypes.c_uint64),
    ]

class EvalVector(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("compile_ok", ctypes.c_float),
        ("test_delta", ctypes.c_float),
        ("regression_risk", ctypes.c_float),
        ("cost", ctypes.c_float),
        ("novelty", ctypes.c_float),
        ("lineage_depth", ctypes.c_float),
    ]

class EventRecord(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("seq", ctypes.c_uint64),
        ("parent_seq", ctypes.c_uint64),
        ("hash_env", ctypes.c_uint64),
        ("agent_id", ctypes.c_uint32),
        ("tick", ctypes.c_uint64),
        ("type_tag", ctypes.c_uint8),
        ("done", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8 * 2),
        ("eval", EvalVector),
        ("obs_offset", ctypes.c_uint64),
        ("obs_len", ctypes.c_uint32),
        ("action_id", ctypes.c_uint32),
        ("model_version", ctypes.c_uint32),
        ("clock_hi", ctypes.c_uint64),
        ("clock_lo", ctypes.c_uint64),
    ]

def scan_sealed_segments(segment_dir: str):
    sealed = []
    for f in os.listdir(segment_dir):
        if f.endswith('.mmap'):
            path = os.path.join(segment_dir, f)
            with open(path, "r+b") as file:
                mm = mmap.mmap(file.fileno(), 0)
                header = SegmentHeader.from_buffer_copy(mm, 0)
                if header.sealed == 1:
                    sealed.append(path)
                mm.close()
    return sealed

def load_segment(filepath: str):
    with open(filepath, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        header = SegmentHeader.from_buffer_copy(mm, 0)
        
        offset = ctypes.sizeof(SegmentHeader)
        records = []
        for _ in range(header.record_count):
            record = EventRecord.from_buffer_copy(mm, offset)
            records.append(record)
            offset += ctypes.sizeof(EventRecord)
            
        mm.close()
        return header, records
