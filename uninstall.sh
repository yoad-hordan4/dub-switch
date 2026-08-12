#!/bin/bash
PLIST="$HOME/Library/LaunchAgents/com.hebrewenglish.switcher.plist"
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "Uninstalled. You can delete this folder manually."
