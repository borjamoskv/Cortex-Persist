# VHS Tape for CORTEX-Persist C5-REAL Demo
# Render with: vhs < cortex_demo.tape

Output assets/marketing/cortex_demo.gif
Output assets/marketing/cortex_demo.mp4

Require cortex
Require sqlite3

Set Theme "Catppuccin Mocha"
Set Width 1200
Set Height 600
Set Padding 40
Set WindowBar Colorful
Set FontSize 16
Set FontFamily "JetBrains Mono"

# Estética Industrial Noir (Black #0A0A0A, Blue #2B3BE5 accents where possible via prompt)
# Here we simulate the terminal output

Type "# 1. Initialize Sovereign Ledger"
Sleep 500ms
Enter
Type "cortex init"
Sleep 500ms
Enter
Sleep 1s

Type "# 2. Store a memory with C5-REAL cryptographic seal"
Sleep 500ms
Enter
Type "cortex memory store risk-bot 'Transaction flagged: IP mismatch'"
Sleep 500ms
Enter
Sleep 2s

Type "# 3. Verify the stored fact lineage"
Sleep 500ms
Enter
Type "cortex verify 1"
Sleep 500ms
Enter
Sleep 2s

Type "# 4. Tamper attempt (direct DB mutation bypass)"
Sleep 500ms
Enter
Type "sqlite3 cortex.db "
Type '"UPDATE facts SET content='
Type "'Transaction approved' "
Type "WHERE id="
Type "'8f4a2b9e'"
Type '"'
Sleep 500ms
Enter
Sleep 1s

Type "# 5. Ledger verification failure (Tamper Detected)"
Sleep 500ms
Enter
Type "cortex trust-ledger verify"
Sleep 500ms
Enter
Sleep 4s

Type "# CORTEX-Persist: Epistemic Containment Achieved."
Sleep 2s
