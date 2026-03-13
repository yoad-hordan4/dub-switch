#!/usr/bin/env python3
"""
Run by app.py in a subprocess to delete n chars and paste replacement text.
Uses osascript + pbcopy/pbpaste to avoid CGEventTap interference.
Usage: inject.py <n_backspaces> <converted_text_as_utf8_hex>
"""
import sys, subprocess

n         = int(sys.argv[1])
converted = bytes.fromhex(sys.argv[2]).decode('utf-8')

# Save current clipboard content
old_clip = subprocess.run(['pbpaste'], capture_output=True).stdout

# Put the converted text into the clipboard
proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
proc.communicate(converted.encode('utf-8'))

# Use osascript/System Events: n backspaces then Cmd+V (paste)
backspace_script = '\n'.join(['    key code 51', '    delay 0.02'] * n)
script = f'''tell application "System Events"
    delay 0.05
{backspace_script}
    delay 0.05
    key code 9 using command down
    delay 0.1
end tell'''

subprocess.run(['osascript', '-e', script])

# Restore clipboard
proc2 = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
proc2.communicate(old_clip)
