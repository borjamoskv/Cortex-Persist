import sys
from cortex.worker.issue_reader import IssueReader

def main():
    test_urls = [
        "https://github.com/fastapi/fastapi/issues/10000",
        "https://github.com/pypa/pip/issues/11500",
        "https://github.com/astral-sh/uv/issues/2500"
    ]
    
    success = 0
    for url in test_urls:
        print(f"Reading: {url}")
        try:
            ctx = IssueReader.read(url)
            print(f"Title: {ctx.title}")
            print(f"Author: {ctx.author}")
            print(f"Labels: {ctx.labels}")
            print(f"Body Length: {len(ctx.body)} chars")
            print(f"Comments: {len(ctx.comments)}")
            print("-" * 40)
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            print("-" * 40)
            
    print(f"Success Rate: {success}/{len(test_urls)}")
    if success != len(test_urls):
        sys.exit(1)

if __name__ == "__main__":
    main()
