#!/usr/bin/env python3
"""
Hebrew-English keyboard switcher.
Listens globally for keystrokes, buffers them, and on Ctrl+1
converts the last typed word/phrase between Hebrew and English layouts.

Mac:     requires Accessibility permission (System Settings > Privacy > Accessibility).
Windows: run as administrator (or grant Accessibility via UAC prompt).
"""

import sys
import time
import threading
import multiprocessing
from pynput import keyboard
from pynput.keyboard import Key
from layout import convert_text, detect_language
from input_source import detect_hebrew_and_english, switch_to

_IS_MAC = sys.platform == 'darwin'

if _IS_MAC:
    from Quartz import (kCGEventKeyDown, CGEventGetFlags,
                        CGEventGetIntegerValueField, kCGKeyboardEventKeycode)

# ── Trigger key ────────────────────────────────────────────────────────────────
# Ctrl+1.  On Mac we intercept and SUPPRESS this combo so it never reaches
# the active text field.  On Windows Ctrl+1 doesn't produce visible characters
# in most apps so suppression is not needed.
_TRIGGER_KEYCODE = 18       # '1' key hardware keycode (Mac)
_CTRL_MASK  = 0x40000       # kCGEventFlagMaskControl (Mac)

if _IS_MAC:
    def _trigger_intercept(event_type, event):
        """Suppress Ctrl+1 so it doesn't reach the focused app (Mac only)."""
        if event_type == kCGEventKeyDown:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags   = CGEventGetFlags(event)
            if keycode == _TRIGGER_KEYCODE and (flags & _CTRL_MASK):
                return None   # suppress
        return event

# How long a pause (seconds) resets the buffer
IDLE_RESET_SECONDS = 5

# ── Input source IDs (auto-detected at startup) ───────────────────────────────
_hebrew_source, _english_source = detect_hebrew_and_english()

# ── Buffer state ──────────────────────────────────────────────────────────────
is_typing = False
buffer = []
buffer_lock = threading.Lock()
_conversion_lock = threading.Lock()
pressed_keys = set()
_reset_timer = None


def reset_buffer():
    global buffer
    with buffer_lock:
        buffer = []


def schedule_idle_reset():
    global _reset_timer
    if _reset_timer:
        _reset_timer.cancel()
    _reset_timer = threading.Timer(IDLE_RESET_SECONDS, reset_buffer)
    _reset_timer.daemon = True
    _reset_timer.start()


# ── Injection worker (runs in a child process) ─────────────────────────────────
# A child process has no CGEventTap, so its injected keystrokes flow directly
# to the focused app without being swallowed or double-processed.
# Works on both Mac and Windows.
def _inject_worker(n, converted):
    """Delete n chars then paste the converted text."""
    import pyperclip
    from pynput.keyboard import Controller as Ctrl, Key as K
    import time as t

    ctrl      = Ctrl()
    paste_mod = K.cmd if _IS_MAC else K.ctrl_l

    old_clip = pyperclip.paste()
    pyperclip.copy(converted)

    t.sleep(0.05)
    for _ in range(n):
        ctrl.press(K.backspace)
        ctrl.release(K.backspace)
        t.sleep(0.02)

    t.sleep(0.05)
    ctrl.press(paste_mod)
    ctrl.press('v')
    ctrl.release('v')
    ctrl.release(paste_mod)
    t.sleep(0.1)

    pyperclip.copy(old_clip)


# ── Trigger logic ─────────────────────────────────────────────────────────────
def do_conversion():
    global buffer, is_typing
    if not _conversion_lock.acquire(blocking=False):
        return  # another conversion is already running
    try:
        with buffer_lock:
            text = ''.join(buffer)
            n    = len(buffer)
            buffer = []

        if not text.strip():
            return

        converted     = convert_text(text)
        original_lang = detect_language(text)

        print(f"[buffer]  {repr(text)}")

        if converted == text:
            print(f"[skip]    no change needed")
            return

        print(f"[convert] ({original_lang}) → {repr(converted)}")

        is_typing = True

        # Wait for Ctrl to be physically released before injecting
        deadline = time.time() + 2.0
        while time.time() < deadline:
            has_ctrl = Key.ctrl_l in pressed_keys or Key.ctrl_r in pressed_keys
            if not has_ctrl:
                break
            time.sleep(0.02)
        time.sleep(0.08)

        # Inject in a child process to keep event routing clean
        p = multiprocessing.Process(target=_inject_worker, args=(n, converted))
        p.start()
        p.join()

        time.sleep(0.1)

        # Switch input source to the language we just converted to
        target = _english_source if original_lang == 'hebrew' else _hebrew_source
        if target:
            switch_to(target)
            print(f"[switch]  → {target}")

    finally:
        time.sleep(0.1)
        with buffer_lock:
            buffer = []   # discard anything that leaked in during injection
        is_typing = False
        _conversion_lock.release()


# ── Keyboard listener callbacks ───────────────────────────────────────────────
def on_press(key):
    pressed_keys.add(key)

    ctrl = Key.ctrl_l in pressed_keys or Key.ctrl_r in pressed_keys

    if ctrl and hasattr(key, 'char') and key.char == '1':
        if not is_typing:
            threading.Thread(target=do_conversion, daemon=True).start()
        return

    if is_typing:
        return

    if ctrl:
        return

    if key == Key.space:
        with buffer_lock:
            buffer.append(' ')
        schedule_idle_reset()
        return

    if hasattr(key, 'char') and key.char:
        with buffer_lock:
            buffer.append(key.char)
        schedule_idle_reset()
        return

    reset_keys = {Key.enter, Key.tab, Key.esc, Key.left, Key.right,
                  Key.up, Key.down, Key.home, Key.end, Key.page_up, Key.page_down}
    if key in reset_keys:
        reset_buffer()
        return

    if key == Key.backspace:
        with buffer_lock:
            if buffer:
                buffer.pop()
        schedule_idle_reset()


def on_release(key):
    pressed_keys.discard(key)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    print("Hebrew-English switcher running.")
    print("Shortcut: Ctrl + 1")
    print(f"Hebrew input source : {_hebrew_source or 'NOT FOUND'}")
    print(f"English input source: {_english_source or 'NOT FOUND'}")
    print("Press Ctrl+C to stop.\n")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        if _IS_MAC:
            listener._intercept = _trigger_intercept
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == '__main__':
    multiprocessing.freeze_support()   # required for PyInstaller on Windows
    main()
