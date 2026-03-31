#!/usr/bin/env python3
import asyncio
import argparse
import sys
import json
from mac_control.cdp_engine import MacControlOmega

async def main():
    parser = argparse.ArgumentParser(description="CDP Actions for Sovereign UI Automation.")
    subparsers = parser.add_subparsers(dest="action", required=True)
    
    # Click
    click_parser = subparsers.add_parser("click", help="Click an element.")
    click_parser.add_argument("target", help="URL substring to match")
    click_parser.add_argument("--selector", required=True, help="CSS selector to click")
    
    # Type
    type_parser = subparsers.add_parser("type", help="Type text into an element.")
    type_parser.add_argument("target", help="URL substring to match")
    type_parser.add_argument("--selector", required=True, help="CSS selector to type into")
    type_parser.add_argument("--text", required=True, help="Text to insert")
    
    # Evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Execute JS")
    eval_parser.add_argument("target", help="URL substring to match")
    eval_parser.add_argument("--js", required=True, help="JS string to execute")

    # Screenshot
    shot_parser = subparsers.add_parser("screenshot", help="Take a screenshot")
    shot_parser.add_argument("target", help="URL substring to match")
    shot_parser.add_argument("--file", required=True, help="Filename to save PNG")
    
    args = parser.parse_args()
    
    ctl = MacControlOmega()
    if not await ctl.connect(args.target):
        sys.exit(1)
        
    try:
        if args.action == "click":
            await ctl.click(args.selector)
            print(f"Clicked {args.selector}")
        elif args.action == "type":
            await ctl.type_text(args.selector, args.text)
            print(f"Typed into {args.selector}")
        elif args.action == "evaluate":
            res = await ctl.evaluate(args.js)
            print(json.dumps({"result": res}))
        elif args.action == "screenshot":
            await ctl.screenshot(args.file)
    finally:
        await ctl.close()

if __name__ == "__main__":
    asyncio.run(main())
