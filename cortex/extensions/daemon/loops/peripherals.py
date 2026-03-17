# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import asyncio
import logging
import re
import subprocess

logger = logging.getLogger("cortex.extensions.daemon.loops.peripherals")


async def peripheral_loop(state):
    while True:
        try:
            proc = await asyncio.create_subprocess_shell(
                'system_profiler SPBluetoothDataType | grep -A 10 "Connected:"',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            devices = {}
            if "AirPods" in output:
                match = re.search(r"Battery Level: (\d+)%", output)
                devices["AirPods"] = {
                    "battery": int(match.group(1)) if match else "??",
                    "connected": True,
                }
            state.daemons["peripherals"]["devices"] = devices
        except OSError as exc:
            logger.debug("Peripheral scan error: %s", exc)
        await asyncio.sleep(10)
