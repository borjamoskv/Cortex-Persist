import json
import os
import sys

try:
    import pypdf
except ImportError:
    print("pypdf completely missing. Please install it.")
    sys.exit(1)

pdf_path = "/Users/borjafernandezangulo/Downloads/Elements_of_Information_Theory_Elements.pdf"

if not os.path.exists(pdf_path):
    print("PDF not found at path.")
    sys.exit(1)

reader = pypdf.PdfReader(pdf_path)
total_pages = len(reader.pages)
print(f"[CORTEX:AUTODIDACT-OMEGA] Ingesting {total_pages} pages...")

theorems = []
definitions = []
word_counts = {
    "entropy": 0,
    "capacity": 0,
    "kolmogorov": 0,
    "typical set": 0,
    "redundancy": 0,
    "data compression": 0,
    "mutual information": 0,
    "complexity": 0
}

for i in range(total_pages):
    page_text = reader.pages[i].extract_text()
    if not page_text:
        continue

    lower_text = page_text.lower()
    for word in word_counts.keys():
        word_counts[word] += lower_text.count(word)

    # Heuristic for finding formal definitions
    lines = page_text.split('\n')
    for line in lines:
        if line.startswith("Theorem"):
            theorems.append({"page": i, "text": line[:150]})
        elif line.startswith("Definition"):
            definitions.append({"page": i, "text": line[:150]})

print("--- OMEGA EPISTEMIC DEMON COMPLETE ---")
print(f"Total Pages Masticated: {total_pages}")
print("Frequency Vectors:", json.dumps(word_counts, indent=2))
print(f"Found {len(theorems)} Theorems and {len(definitions)} Definitions.")

out_path = "/Users/borjafernandezangulo/.gemini/antigravity/brain/ee6e4ae2-67ec-433e-a8bc-b45e734dd062/elements_full_stats.json"
with open(out_path, "w") as f:
    json.dump({
        "total_pages": total_pages,
        "word_counts": word_counts,
        "theorems_preview": theorems[:30],
        "definitions_preview": definitions[:30]
    }, f, indent=2)

print(f"Crystallized dataset to: {out_path}")
