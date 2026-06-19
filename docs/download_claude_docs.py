import os
import aiohttp
import asyncio
import xml.etree.ElementTree as ET

SITEMAP_URL = "https://docs.anthropic.com/sitemap.xml"
OUTPUT_DIR = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/docs/claude_docs"

async def fetch(session, url, retries=3):
    md_url = url + ".md"
    for attempt in range(retries):
        try:
            async with session.get(md_url) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 404:
                    print(f"404 Not Found: {md_url}")
                    return None
        except Exception as e:
            if attempt == retries - 1:
                print(f"Error fetching {md_url}: {e}")
            await asyncio.sleep(1)
    return None

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    async with aiohttp.ClientSession() as session:
        print(f"Fetching sitemap from {SITEMAP_URL}...")
        async with session.get(SITEMAP_URL) as response:
            sitemap_content = await response.text()
            
        root = ET.fromstring(sitemap_content)
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = []
        for url_element in root.findall('sm:url', namespace):
            loc = url_element.find('sm:loc', namespace)
            if loc is not None and "platform.claude.com/docs/en/" in loc.text:
                urls.append(loc.text)
                
        print(f"Found {len(urls)} English document URLs.")
        
        tasks = []
        for url in urls:
            tasks.append(process_url(session, url))
            
        await asyncio.gather(*tasks)

async def process_url(session, url):
    content = await fetch(session, url)
    if content:
        # Extract path relative to /docs/en/
        path_part = url.split("platform.claude.com/docs/en/")[1]
        if not path_part:
            path_part = "index"
        file_path = os.path.join(OUTPUT_DIR, f"{path_part}.md")
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved: {file_path}")

if __name__ == "__main__":
    asyncio.run(main())
