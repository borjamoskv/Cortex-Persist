import time
import os
from ingestor import scan_sealed_segments, load_segment

def main():
    print("C5-REAL CONSUMER: Despertando. Esperando señal del Productor...")
    dir_path = "/tmp/cortex_stress"
    
    # Wait for directory to exist
    while not os.path.exists(dir_path):
        time.sleep(0.1)
        
    total_records = 0
    expected_records = 200000
    start_time = time.time()
    
    processed = set()
    
    while total_records < expected_records:
        sealed = scan_sealed_segments(dir_path)
        for s in sealed:
            if s not in processed:
                header, records = load_segment(s)
                total_records += len(records)
                processed.add(s)
                
        if time.time() - start_time > 10: # Timeout safety
            print("C5-REAL CONSUMER: Timeout alcanzado.")
            break
            
        time.sleep(0.05)

    elapsed = time.time() - start_time
    print(f"C5-REAL CONSUMER: Ingeridos {total_records} eventos en {elapsed:.3f} seg.")
    
    if total_records == expected_records:
        print("VEREDICTO: Lossless IPC Confirmado (0% pérdida de Entropía).")
        exit(0)
    else:
        print(f"VEREDICTO: Falla Termodinámica (Leídos {total_records} de {expected_records}).")
        exit(1)

if __name__ == "__main__":
    main()
