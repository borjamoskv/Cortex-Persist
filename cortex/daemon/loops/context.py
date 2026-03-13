# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import asyncio
import logging
import re
import time

from cortex.daemon.utils import run_osascript

logger = logging.getLogger("cortex.daemon.loops.context")


async def capture_context(state, project_name: str, speak_func):
    try:
        script = """
        tell application "System Events"
            set frontApp to name of first process whose frontmost is true
            tell process frontApp
                set windowTitle to name of window 1
                set windowBounds to bounds of window 1
                return {frontApp, windowTitle, windowBounds}
            end tell
        end tell
        """
        res = await run_osascript(script)
        if res:
            parts = [p.strip() for p in res.split(", ")]
            if len(parts) >= 3:
                app_name = parts[0]
                title = parts[1]
                raw_bounds = res.split(title)[-1].strip(", ")
                bounds = re.findall(r"\d+", raw_bounds)

                if len(bounds) == 4:
                    if "context_map" not in state.daemons["gidatu"]:
                        state.daemons["gidatu"]["context_map"] = {}

                    if project_name not in state.daemons["gidatu"]["context_map"]:
                        state.daemons["gidatu"]["context_map"][project_name] = {}

                    state.daemons["gidatu"]["context_map"][project_name][app_name] = {
                        "window_title": title,
                        "bounds": bounds,
                        "captured_at": time.time(),
                    }
                    await speak_func(state, f"Contexto capturado para {project_name}: {app_name}.")
                    state.save_state()
    except Exception as e:
        logger.error("Capture Context Error: %s", e)


async def restore_context(state, project_name: str, speak_func):
    context = state.daemons["gidatu"].get("context_map", {}).get(project_name)
    if not context:
        await speak_func(state, f"No hay contexto guardado para {project_name}.")
        return

    await speak_func(state, f"Ejecutando Deep Restore para {project_name}.")
    for app_name, details in context.items():
        try:
            bounds = details.get("bounds")
            if bounds and len(bounds) == 4:
                x, y, x2, y2 = map(int, bounds)
                width = x2 - x
                height = y2 - y

                script = f'''
                tell application "{app_name}" to activate
                delay 0.5
                tell application "System Events"
                    tell process "{app_name}"
                        set frontmost to true
                        try
                            set position of window 1 to {{{x}, {y}}}
                            set size of window 1 to {{{width}, {height}}}
                        on error
                            set bounds of window 1 to {{{x}, {y}, {x2}, {y2}}}
                        end try
                    end tell
                end tell
                '''
                await run_osascript(script)
            else:
                script = f'tell application "{app_name}" to activate'
                await run_osascript(script)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error("Restore Error (%s): %s", app_name, e)


async def gidatu_loop(state):
    state.daemons["gidatu"]["status"] = "online"
    try:
        while True:
            try:
                script = 'tell application "System Events" to name of first process whose frontmost is true'
                app_name = await run_osascript(script)
                app_name = app_name.strip() if app_name else ""
                state.daemons["gidatu"]["active_app"] = app_name
                state.daemons["gidatu"]["current_app"] = app_name

                win_title = ""
                if app_name:
                    try:
                        title_script = f'tell application "System Events" to tell process "{app_name}" to get name of window 1'
                        win_title = await run_osascript(title_script)
                    except Exception:
                        pass
                state.daemons["gidatu"]["window_title"] = win_title

                prev_context = state.daemons["gidatu"].get("current_context")
                new_context = None

                search_str = f"{app_name} {win_title}".lower()
                for proj in ["cortex", "moltbook", "naroa", "notch", "alba", "trompetas"]:
                    if proj in search_str:
                        new_context = proj
                        break

                if new_context and new_context != prev_context:
                    state.daemons["gidatu"]["current_context"] = new_context

                await asyncio.sleep(2)
            except Exception as e:
                print(f"Gidatu Loop Error: {e}")
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        state.daemons["gidatu"]["status"] = "offline"
        raise
