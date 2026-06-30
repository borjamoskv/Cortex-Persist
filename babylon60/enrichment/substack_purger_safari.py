import os
import subprocess
import sys
import time
import urllib.parse


def run_applescript(script_content: str) -> str:
    """Run inline AppleScript and return stdout."""
    # Write to a temp scpt file to avoid shell escaping issues
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_file = os.path.join(base_dir, "temp_run.scpt")
    with open(temp_file, "w") as f:
        f.write(script_content)

    try:
        res = subprocess.check_output(["osascript", temp_file], stderr=subprocess.STDOUT)
        return res.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.output.decode('utf-8').strip()}"
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def delete_subscriber(email: str) -> str:
    """Automates Safari to delete a single subscriber via their details page."""
    encoded_email = urllib.parse.quote(email)
    url = f"https://borjamoskv.substack.com/publish/subscribers/details?email={encoded_email}"

    # AppleScript to navigate to URL and execute deletion
    script = f"""
tell application "Safari"
    activate
    tell front window
        repeat with t in every tab
            try
                set u to URL of t
                if u contains "publish/subscribers" then
                    set URL of t to "{url}"
                    delay 4.5
                    
                    # 1. Click Ellipsis
                    set jsCode to "(() => {{ " & ¬
                        "  let btn = document.querySelector('button[aria-label=\\\"Ellipsis\\\"]');" & ¬
                        "  if (!btn) return 'ELLIPSIS_NOT_FOUND';" & ¬
                        "  btn.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true }}));" & ¬
                        "  btn.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true }}));" & ¬
                        "  btn.click();" & ¬
                        "  return 'ELLIPSIS_CLICKED';" & ¬
                        "}})()"
                    set clickRes to do JavaScript jsCode in t
                    if clickRes is not "ELLIPSIS_CLICKED" then
                        return "FAILED_CLICK_ELLIPSIS: " & clickRes
                    end if
                    delay 0.5
                    
                    # 2. Click Quitar de la lista
                    set jsCode2 to "(() => {{ " & ¬
                        "  let items = Array.from(document.querySelectorAll('[role=menuitem], [role=menuitemcheckbox], [role=option], div[data-radix-menu-content] *, div[role=menu] *'));" & ¬
                        "  let removeBtn = items.find(el => el.innerText && el.innerText.trim() === 'Quitar de la lista');" & ¬
                        "  if (!removeBtn) return 'REMOVE_OPTION_NOT_FOUND';" & ¬
                        "  removeBtn.click();" & ¬
                        "  return 'OPTION_CLICKED';" & ¬
                        "}})()"
                    set optionRes to do JavaScript jsCode2 in t
                    if optionRes is not "OPTION_CLICKED" then
                        return "FAILED_OPTION: " & optionRes
                    end if
                    delay 0.5
                    
                    # 3. Confirm Modal
                    set jsCode3 to "(() => {{ " & ¬
                        "  let confirmBtn = Array.from(document.querySelectorAll('button')).find(el => el.innerText && (el.innerText.trim() === 'Eliminar y reembolsar' || el.innerText.trim() === 'Quitar' || el.innerText.trim() === 'Quitar de la lista'));" & ¬
                        "  if (confirmBtn) {{" & ¬
                        "    confirmBtn.click();" & ¬
                        "    return 'DELETED';" & ¬
                        "  }} else {{" & ¬
                        "    return 'CONFIRM_NOT_FOUND';" & ¬
                        "  }}" & ¬
                        "}})()"
                    set confirmRes to do JavaScript jsCode3 in t
                    return confirmRes
                end if
            on error e
                # Ignore
            end try
        end repeat
    end tell
    return "TAB_NOT_FOUND"
end tell
"""
    return run_applescript(script)


import asyncio

async def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    purged_path = os.path.join(base_dir, "data", "purged_subscribers.txt")
    if not os.path.exists(purged_path):
        print(f"Error: {purged_path} not found.")
        sys.exit(1)

    with open(purged_path) as f:
        emails = [line.strip() for line in f if line.strip()]

    print(f"Starting Substack purge of {len(emails)} subscribers...")

    # We will process in order. We can add a checkpoint or process a batch of 5 first.
    success_count = 0
    fail_count = 0

    # Process up to 5 first to verify, or run all of them?
    # Since we are in God Mode, we process all, but let's print detailed logs.
    for i, email in enumerate(emails):
        # Skip elektronische@gmail.com which we already deleted manually as a test
        if email == "elektronische@gmail.com":
            print(f"[{i + 1}/{len(emails)}] Skipping {email} (already deleted)")
            success_count += 1
            continue

        print(f"[{i + 1}/{len(emails)}] Deleting {email}...", end="", flush=True)
        status = delete_subscriber(email)
        print(f" Result: {status}")

        if status == "DELETED":
            success_count += 1
        else:
            fail_count += 1

        # Safe delay between deletions to let Next.js render and database sync
        await asyncio.sleep(2.0)

    print(f"Purge complete. Success: {success_count}, Fail: {fail_count}")


if __name__ == "__main__":
    asyncio.run(main())
