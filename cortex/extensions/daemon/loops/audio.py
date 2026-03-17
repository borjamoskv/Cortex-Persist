# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import asyncio
import logging

from cortex.extensions.daemon.utils import run_osascript

logger = logging.getLogger("cortex.extensions.daemon.loops.audio")


async def audio_mixer_loop(state):
    while True:
        try:
            found_active = False
            for app_name in ["Spotify", "Music"]:
                script = (
                    f'if application "{app_name}" is running then '
                    f'tell application "{app_name}" to get '
                    "{player state, sound volume, artist of current track, name of current track}"
                )
                res = await run_osascript(script)
                if res:
                    parts = [p.strip() for p in res.split(", ")]
                    if len(parts) >= 2:
                        is_playing = "playing" in parts[0]
                        state.daemons["audio_mixer"]["lines"][app_name]["active"] = is_playing
                        state.daemons["audio_mixer"]["lines"][app_name]["vol"] = int(parts[1])

                        if is_playing and len(parts) >= 4:
                            state.daemons["audio_mixer"]["now_playing"]["artist"] = parts[2]
                            state.daemons["audio_mixer"]["now_playing"]["track"] = parts[3]
                            state.daemons["audio_mixer"]["now_playing"]["app"] = app_name
                            found_active = True

            if not found_active:
                state.daemons["audio_mixer"]["now_playing"]["app"] = None

            res = await run_osascript("output volume of (get volume settings)")
            if res:
                state.daemons["audio_mixer"]["master"] = int(res)

        except (OSError, ValueError) as exc:
            logger.debug("Audio mixer poll error: %s", exc)
        await asyncio.sleep(5)
