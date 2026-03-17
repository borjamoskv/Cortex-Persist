#!/bin/bash
# Sovereign Watchdog v1.1 - Aether Blue YL Persistence
WALLPAPER_PATH="/Users/borjafernandezangulo/.gemini/antigravity/brain/3cddd4a0-ce48-4557-bce0-74246ec21a07/aether_blue_yl_wallpaper_5k_1773745455008.png"

while true; do
    # Force apply wallpaper to all desktops
    osascript -e "tell application \"System Events\" to set picture of every desktop to POSIX file \"$WALLPAPER_PATH\""
    
    # Ensure system settings are locked in
    defaults write com.apple.universalaccess reduceTransparency -bool true
    defaults write com.apple.universalaccess increaseContrast -bool true
    
    # Set System Accent to Blue (5)
    defaults write -g AppleAccentColor -int 5
    
    # Hide the Dock properly
    defaults write com.apple.dock autohide -bool true
    defaults write com.apple.dock tilesize -int 36
    
    # Sleep for 15 seconds to minimize CPU but maintain control
    sleep 15
done
