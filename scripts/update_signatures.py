#!/usr/bin/env python3
"""
[C5-REAL] Exergy-Maximized Signature Automation Protocol
Proof: { Base: AST-Parsing + Idempotent Injection, Range: [0,1], Confidence: C5-REAL }
"""

import re
import sys
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parents[1] / "src" / "pages" / "blog"

def main() -> int:
    if not BLOG_DIR.exists():
        print(f"Error: Blog directory {BLOG_DIR} does not exist.")
        return 1

    # Find all .astro files in the blog directory (excluding index.astro)
    astro_files = []
    for f in BLOG_DIR.glob("*.astro"):
        if f.name != "index.astro":
            astro_files.append(f)

    # Gather metadata
    articles = []
    for f in astro_files:
        try:
            content = f.read_text(encoding="utf-8")
        except OSError as e:
            print(f"Error reading {f.name}: {e}")
            continue
        
        # Extract title from <h1>
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
        title = h1_match.group(1).strip() if h1_match else f.stem.replace("_", " ").title()
        
        # Clean title from HTML tags and extra whitespaces
        title = re.sub(r"<[^>]+>", "", title)
        title = " ".join(title.split())
        
        url = f"/blog/{f.stem}"
        articles.append({
            "path": f,
            "title": title,
            "url": url,
            "content": content
        })

    # Sort articles so order is deterministic
    articles.sort(key=lambda x: x["title"])

    print(f"Loaded {len(articles)} articles for signature automation.")

    # Update each article
    for current in articles:
        # Build links to other articles (div-based to avoid CSS class pollution on list items)
        other_links = []
        for other in articles:
            if other["path"] == current["path"]:
                continue
            link_html = f"""                <div style="margin: 0; padding: 0 0 0 16px; font-size: 0.95rem; position: relative; line-height: 1.5;">
                    <span style="position: absolute; left: 0; color: var(--yinmn-blue); font-family: var(--font-mono);">►</span>
                    <a href="{other['url']}" style="color: var(--parchment-white); text-decoration: none; border-bottom: 1px dotted rgba(243, 244, 246, 0.3); transition: var(--transition-smooth);">{other['title']}</a>
                </div>"""
            other_links.append(link_html)

        links_block = "\n".join(other_links)

        signature_html = f"""<!-- CORTEX-SIGNATURE-START -->
        <div style="margin: 60px 0 40px; padding: 28px; background: rgba(255, 255, 255, 0.01); border: 1px solid var(--mica-border); border-radius: var(--radius-soft); font-family: var(--font-primary);">
            <div style="border-left: 3px solid var(--yinmn-blue); padding-left: 14px; margin-bottom: 20px;">
                <h4 style="margin: 0; color: var(--yinmn-blue); text-transform: uppercase; font-family: var(--font-mono); font-size: 0.8rem; letter-spacing: 0.15em;">[C5-REAL] Cortex-Persist Cognitive Routing</h4>
                <p style="margin: 4px 0 0 0; font-size: 0.75rem; color: rgba(243, 244, 246, 0.4);">Artículos y Enjambres Relacionados</p>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
{links_block}
            </div>
        </div>
        <!-- CORTEX-SIGNATURE-END -->"""

        content = current["content"]
        
        # Ensure placeholders exist
        if "<!-- CORTEX-SIGNATURE-START -->" not in content:
            # Inject placeholders right before <div class="footer-terminal">
            terminal_div = '<div class="footer-terminal">'
            if terminal_div in content:
                content = content.replace(terminal_div, f"<!-- CORTEX-SIGNATURE-START -->\n<!-- CORTEX-SIGNATURE-END -->\n\n        {terminal_div}")
            else:
                # Fallback: right before </body>
                content = content.replace("</body>", f"<!-- CORTEX-SIGNATURE-START -->\n<!-- CORTEX-SIGNATURE-END -->\n</body>")

        # Replace signature between placeholders
        pattern = r"<!-- CORTEX-SIGNATURE-START -->.*?<!-- CORTEX-SIGNATURE-END -->"
        updated_content = re.sub(pattern, signature_html, content, flags=re.DOTALL)

        if updated_content != current["content"]:
            try:
                current["path"].write_text(updated_content, encoding="utf-8")
                print(f"Updated signature in: {current['path'].name}")
            except OSError as e:
                print(f"Error writing to {current['path'].name}: {e}")
                return 1
        else:
            print(f"Signature already up-to-date in: {current['path'].name}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
