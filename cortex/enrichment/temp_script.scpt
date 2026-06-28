tell application "Safari"
    tell front window
        repeat with t in every tab
            try
                set u to URL of t
                if u contains "details?email=" then
                    set jsCode to "(() => { " & ¬
                        "  let confirmBtn = Array.from(document.querySelectorAll('button')).find(el => el.innerText && (el.innerText.trim() === 'Eliminar y reembolsar' || el.innerText.trim() === 'Quitar' || el.innerText.trim() === 'Quitar de la lista'));" & ¬
                        "  if (confirmBtn) {" & ¬
                        "    confirmBtn.click();" & ¬
                        "    return 'DELETED_OK';" & ¬
                        "  } else {" & ¬
                        "    return 'CONFIRM_NOT_FOUND';" & ¬
                        "  }" & ¬
                        "})()"
                    set res to do JavaScript jsCode in t
                    return res
                end if
            on error e
                # Ignore
            end try
        end repeat
    end tell
    return "NOT_FOUND"
end tell
