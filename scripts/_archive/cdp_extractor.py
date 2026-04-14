#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys

from mac_control.cdp_engine import MacControlOmega


async def main():
    parser = argparse.ArgumentParser(description="CDP Extractor for Sovereign UI Automation.")
    parser.add_argument("target", help="URL substring to match the Chrome tab.")
    parser.add_argument(
        "--selector", type=str, help="CSS selector to extract. If omitted, extracts entire page."
    )
    parser.add_argument("--html", action="store_true", help="Extract raw HTML instead of text.")
    parser.add_argument("--json", action="store_true", help="Format output as JSON.")
    parser.add_argument("--file", type=str, help="Save extracted content to file.")

    args = parser.parse_args()

    ctl = MacControlOmega()
    if not await ctl.connect(args.target):
        sys.exit(1)

    try:
        if args.selector:
            content = await ctl.extract_selector(args.selector, extract_html=args.html)
        else:
            content = await ctl.extract_page(extract_html=args.html)

        if content is None:
            if args.json:
                print(json.dumps({"error": "Selector not found or evaluation failed"}))
            else:
                print("Error: Extracted nothing.")
            sys.exit(1)

        if args.file:
            with open(args.file, "w", encoding="utf-8") as f:
                f.write(content)
            if not args.json:
                print(f"Content saved to {args.file}")

        if args.json:
            print(
                json.dumps({"target": args.target, "selector": args.selector, "content": content})
            )
        elif not args.file:
            print(content)

    finally:
        await ctl.close()


if __name__ == "__main__":
    asyncio.run(main())
