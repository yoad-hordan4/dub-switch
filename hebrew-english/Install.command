#!/bin/bash
# HebrewEnglishSwitcher — Installer
# Double-click this file to install and launch the app.

DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/HebrewEnglishSwitcher.app"

if [ ! -d "$APP" ]; then
    echo "Error: HebrewEnglishSwitcher.app not found."
    echo "Make sure Install.command and HebrewEnglishSwitcher.app are in the same folder."
    read -p "Press Enter to close..."
    exit 1
fi

echo "=== HebrewEnglishSwitcher Installer ==="
echo ""
echo "Removing macOS quarantine flag..."
xattr -cr "$APP"

echo "Launching app..."
open "$APP"

echo ""
echo "Done! HebrewEnglishSwitcher is now running."
echo ""
echo "One more step — grant Accessibility permission:"
echo "  System Settings → Privacy & Security → Accessibility"
echo "  Click + and add HebrewEnglishSwitcher"
echo ""
echo "You can close this window."
