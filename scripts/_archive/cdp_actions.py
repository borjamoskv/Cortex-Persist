#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys

from mac_control.cdp_engine import MacControlOmega

logging.basicConfig(level=logging.ERROR)


async def main():
    parser = argparse.ArgumentParser(description="CDP Action Orchestrator for Mac Control.")
    parser.add_argument("target", help="URL substring to match the Chrome tab.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--click", type=str, help="CSS selector to click.")
    group.add_argument(
        "--type",
        type=str,
        nargs=2,
        metavar=("SELECTOR", "TEXT"),
        help="CSS selector and text to type.",
    )
    group.add_argument("--evaluate", type=str, help="JS code to evaluate.")
    group.add_argument("--screenshot", type=str, help="Take a screenshot and save to path.")

    parser.add_argument("--wait", type=int, default=0, help="Wait N seconds before action.")

    args = parser.parse_args()

    ctl = MacControlOmega()
    if not await ctl.connect(args.target):
        sys.exit(1)

    try:
        if args.wait > 0:
            await asyncio.sleep(args.wait)

        if args.click:
            await ctl.click(args.click)
            print(f"Clicked: {args.click}")
        elif args.type:
            await ctl.type_text(args.type[0], args.type[1])
            print(f"Typed '{args.type[1]}' into {args.type[0]}")
        elif args.evaluate:
            res = await ctl.evaluate(args.evaluate)
            print(f"Result: {res}")
        elif args.screenshot:
            await ctl.screenshot(args.screenshot)

    except Exception as e:
        print(f"Action failed: {e}")
        sys.exit(1)
    finally:
        await ctl.close()


if __name__ == "__main__":
    asyncio.run(main())
