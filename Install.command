#!/bin/bash
# DubSwitch — Installer
# Double-click this file to install and launch the app.

DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/DubSwitch.app"

if [ ! -d "$APP" ]; then
    echo "Error: DubSwitch.app not found."
    echo "Make sure Install.command and DubSwitch.app are in the same folder."
    read -p "Press Enter to close..."
    exit 1
fi

echo "=== DubSwitch Installer ==="
echo ""
echo "Removing macOS quarantine flag..."
xattr -cr "$APP"

echo "Launching app..."
open "$APP"

echo ""
echo "Done! DubSwitch is now running."
echo "Look for the ⌨ icon in your menu bar."
echo ""
echo "One more step — grant permissions:"
echo "  System Settings → Privacy & Security → Accessibility → add DubSwitch"
echo "  System Settings → Privacy & Security → Input Monitoring → add DubSwitch"
echo ""
echo "You can close this window."
