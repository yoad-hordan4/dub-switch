#!/usr/bin/env python3
from pynput import keyboard
from pynput.keyboard import Key

buffer = []

def on_press(key):
    if hasattr(key, 'char') and key.char:
        buffer.append(key.char)
        print(f"buffer: {''.join(buffer)!r}")
    elif key == Key.backspace:
        if buffer:
            buffer.pop()
        print(f"buffer: {''.join(buffer)!r}")
    elif key in {Key.enter, Key.tab, Key.esc, Key.left, Key.right,
                 Key.up, Key.down}:
        buffer.clear()
        print("buffer: (cleared)")

def on_release(key):
    pass

print("Type anything. Press Ctrl+C to stop.\n")
with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
    try:
        l.join()
    except KeyboardInterrupt:
        pass
