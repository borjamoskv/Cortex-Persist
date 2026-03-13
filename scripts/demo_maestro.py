#!/usr/bin/env python3
"""
Sovereign MAC-Ω Integration Test
Provides an interactive demonstration of cortex.ui_control module.

Warning: Requires macOS Accessibility and Automation permissions.
"""

import asyncio
import sys

from cortex.ui_control import MaestroUI, AppTarget

async def run_demo():
    print("=== MAC-Ω: UI Control Demonstration ===")
    print("This script will attempt to:")
    print("1. Open TextEdit")
    print("2. Type a message")
    print("3. Try to click 'File > Export as PDF...'")
    print("\nIf permissions are missing, macOS will prompt you, and this may crash.")
    print("Press ENTER to start or CTRL+C to abort.")
    
    input()
    
    maestro = MaestroUI()
    target = AppTarget(name="TextEdit")
    
    print("\n1. Activating TextEdit...")
    res = await maestro.activate_app(target)
    if not res.success:
        print(f"FAILED to activate TextEdit: {res.error}")
        sys.exit(1)
        
    # Esperamos a que la app termine de cargar (O(1) pragmático)
    await asyncio.sleep(1.5)
    
    print("2. Typing message into active window...")
    mensaje = "CORTEX MAC-OMEGA INITIALIZED."
    for char in mensaje:
        res = await maestro.inject_keystroke(target, char)
        if not res.success:
            print(f"FAILED to type '{char}': {res.error}")
            break
        await asyncio.sleep(0.05)
        
    await asyncio.sleep(1)
            
    print("3. Attempting to click File > Export as PDF...")
    res = await maestro.click_menu_item(target, ["File", "Export as PDF…"])
    if not res.success:
        print(f"FAILED to click menu (This is common if strings are localized or differ): {res.error}")
        
    print("\nDemo finished.")


if __name__ == "__main__":
    asyncio.run(run_demo())
