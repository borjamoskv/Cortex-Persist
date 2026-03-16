#!/bin/bash
set -e

APP_NAME="AetherDrop"
BUNDLE_DIR="$APP_NAME.app"
CONTENTS_DIR="$BUNDLE_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

echo "Building $APP_NAME..."

mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Compile Swift files
swiftc -o "$MACOS_DIR/$APP_NAME" \
    Sources/AetherDropApp.swift \
    Sources/AppDelegate.swift \
    Sources/DropView.swift \
    Sources/NotchOverlayWindow.swift \
    Sources/NotchUI.swift \
    -framework Cocoa \
    -framework SwiftUI

# Copy Info.plist
cp Info.plist "$CONTENTS_DIR/Info.plist"

echo "Build successful: $BUNDLE_DIR"
