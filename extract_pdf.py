import sys
from pypdf import PdfReader

pdf_path = "/Users/borjafernandezangulo/.gemini/antigravity/brain/2bf92ab9-b546-48e5-9c56-9341c0985306/.tempmediaStorage/64c61ec9ec71d2bd.pdf"
out_path = "/tmp/paper.txt"

reader = PdfReader(pdf_path)
text = []
for page in reader.pages:
    text.append(page.extract_text())

with open(out_path, "w") as f:
    f.write("\n".join(text))

print(f"Extracted {len(reader.pages)} pages to {out_path}")
