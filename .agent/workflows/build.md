<!-- [C5-REAL] Exergy-Maximized -->
---
description: Build and run LiveNotch macOS app
---

# 🔨 Build LiveNotch

## Quick Build

// turbo
1. Build the project:
```bash
cd ~/notch-live && swift build 2>&1 | tail -20
```

## Release Build

2. Build with optimizations:
```bash
cd ~/notch-live && swift build -c release 2>&1 | tail -20
```

## Run

3. Run the application:
```bash
cd ~/notch-live && swift run LiveNotch
```

## Clean Build

4. Clean and rebuild from scratch:
```bash
cd ~/notch-live && swift package clean && swift build 2>&1 | tail -30
```
