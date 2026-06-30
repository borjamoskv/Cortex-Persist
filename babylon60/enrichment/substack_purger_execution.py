import os
import sys

from babylon60.enrichment.subscriber_triage import process_batch


def run_purge():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(base_dir, "data", "raw_subscribers.txt")
    cleaned_path = os.path.join(base_dir, "data", "cleaned_subscribers.txt")
    purged_path = os.path.join(base_dir, "data", "purged_subscribers.txt")
    
    if not os.path.exists(raw_path):
        print(f"Error: {raw_path} not found.")
        sys.exit(1)
        
    with open(raw_path) as f:
        emails = [line.strip() for line in f if line.strip()]
        
    matrix = process_batch(emails)
    
    cleaned = []
    purged = []
    
    for email, meta in matrix.items():
        if meta["ppi_reality"] >= 5:
            cleaned.append(email)
        else:
            purged.append(email)
            
    with open(cleaned_path, "w") as f:
        f.write("\n".join(cleaned) + "\n")
        
    with open(purged_path, "w") as f:
        f.write("\n".join(purged) + "\n")
        
    print("Purge complete.")
    print(f"  Total processed: {len(emails)}")
    print(f"  Cleaned (kept):  {len(cleaned)}")
    print(f"  Purged (removed): {len(purged)}")

if __name__ == "__main__":
    run_purge()
