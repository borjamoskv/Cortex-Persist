import os
import urllib.request


def download_and_extract_pdf(url):
    print(f"Downloading PDF from {url}...")
    try:
        import PyPDF2
    except ImportError:
        print("PyPDF2 not found. Generating a script to install and run.")
        os.system("pip install PyPDF2")
        import PyPDF2

    temp_pdf = os.path.expanduser("~/.cortex/temp_arakatu.pdf")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    with urllib.request.urlopen(req) as response, open(temp_pdf, "wb") as out_file:
        data = response.read()
        out_file.write(data)

    print(f"Downloaded temporarily to {temp_pdf}")

    texto = ""
    with open(temp_pdf, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            texto += f"\n--- PAGE {i} ---\n"
            texto += page.extract_text() or ""

    # Save text locally
    out_txt = os.path.expanduser(f"~/.cortex/{url.split('/')[-1]}.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(texto)

    print(f"Extracted {len(texto)} characters to {out_txt}")

    # Remove temp pdf
    os.remove(temp_pdf)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://services.google.com/fh/files/misc/ai_agents_handbook.pdf"
    download_and_extract_pdf(url)
