---
description: Build and run LiveNotch macOS app
---

# 🔨 Build LiveNotch

## Quick Build

// turbo
1. Build the project:
```bash
swift build 2>&1 | tail -20
```

## Release Build

// turbo
2. Build with optimizations:
```bash
swift build -c release 2>&1 | tail -20
```

## Run

// turbo
3. Run the application:
```bash
swift run LiveNotch
```

## Clean Build

// turbo
4. Clean and rebuild from scratch:
```bash
swift package clean && swift build 2>&1 | tail -30
```
