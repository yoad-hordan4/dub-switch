"""
Input source / keyboard layout switcher.
Mac:     uses Carbon TIS API via ctypes (no external deps).
Windows: uses user32 LoadKeyboardLayout + AttachThreadInput via ctypes.
"""

import sys

# ── macOS ──────────────────────────────────────────────────────────────────────
if sys.platform == 'darwin':
    import ctypes

    _carbon = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Carbon.framework/Carbon')
    _cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')

    _carbon.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
    _carbon.TISCopyCurrentKeyboardInputSource.argtypes = []
    _carbon.TISCreateInputSourceList.restype = ctypes.c_void_p
    _carbon.TISCreateInputSourceList.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    _carbon.TISSelectInputSource.restype = ctypes.c_int
    _carbon.TISSelectInputSource.argtypes = [ctypes.c_void_p]
    _carbon.TISGetInputSourceProperty.restype = ctypes.c_void_p
    _carbon.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    _cf.CFArrayGetCount.restype = ctypes.c_long
    _cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
    _cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
    _cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
    _cf.CFStringGetCString.restype = ctypes.c_bool
    _cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    _cf.CFRelease.argtypes = [ctypes.c_void_p]

    _kCFStringEncodingUTF8 = 0x08000100
    _kTISPropertyInputSourceID = ctypes.c_void_p.in_dll(_carbon, 'kTISPropertyInputSourceID')

    def _cf_string_get(ref):
        buf = ctypes.create_string_buffer(512)
        ok = _cf.CFStringGetCString(ref, buf, 512, _kCFStringEncodingUTF8)
        return buf.value.decode('utf-8') if ok else ''

    def _get_source_id(source):
        id_ref = _carbon.TISGetInputSourceProperty(source, _kTISPropertyInputSourceID.value)
        return _cf_string_get(id_ref) if id_ref else ''

    def get_all_source_ids():
        sources = _carbon.TISCreateInputSourceList(None, False)
        count = _cf.CFArrayGetCount(sources)
        ids = [_get_source_id(_cf.CFArrayGetValueAtIndex(sources, i)) for i in range(count)]
        _cf.CFRelease(sources)
        return ids

    def get_current_source_id():
        source = _carbon.TISCopyCurrentKeyboardInputSource()
        sid = _get_source_id(source) if source else ''
        if source:
            _cf.CFRelease(source)
        return sid

    def switch_to(target_id):
        """Switch the active input source to target_id. Returns True on success."""
        sources = _carbon.TISCreateInputSourceList(None, False)
        count = _cf.CFArrayGetCount(sources)
        found = False
        for i in range(count):
            source = _cf.CFArrayGetValueAtIndex(sources, i)
            if _get_source_id(source) == target_id:
                _carbon.TISSelectInputSource(source)
                found = True
                break
        _cf.CFRelease(sources)
        return found

    def detect_hebrew_and_english():
        """
        Auto-detect the Hebrew and English/Latin input source IDs.
        Returns (hebrew_id, english_id) — either may be None if not found.
        """
        hebrew_id = None
        english_id = None
        for sid in get_all_source_ids():
            sl = sid.lower()
            if 'hebrew' in sl and hebrew_id is None:
                hebrew_id = sid
            if hebrew_id != sid and ('us' in sl or '.abc' in sl or 'british' in sl or 'qwerty' in sl) and english_id is None:
                english_id = sid
        return hebrew_id, english_id


# ── Windows ────────────────────────────────────────────────────────────────────
elif sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes

    _user32   = ctypes.WinDLL('user32', use_last_error=True)
    _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    _user32.LoadKeyboardLayoutW.restype  = ctypes.c_void_p
    _user32.LoadKeyboardLayoutW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
    _user32.GetForegroundWindow.restype  = ctypes.c_void_p
    _user32.GetWindowThreadProcessId.restype  = ctypes.c_uint
    _user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
    _user32.AttachThreadInput.restype  = ctypes.c_bool
    _user32.AttachThreadInput.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_bool]
    _user32.ActivateKeyboardLayout.restype  = ctypes.c_void_p
    _user32.ActivateKeyboardLayout.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    _kernel32.GetCurrentThreadId.restype = ctypes.c_uint

    # Standard locale ID strings (leading-zero 8-char hex)
    _HEBREW_LOCALE  = '0000040d'   # Hebrew - Israel
    _ENGLISH_LOCALE = '00000409'   # English - United States

    _KLF_ACTIVATE = 0x00000001

    def detect_hebrew_and_english():
        """Returns the locale ID strings for Hebrew and English layouts."""
        return _HEBREW_LOCALE, _ENGLISH_LOCALE

    def switch_to(locale_str):
        """
        Switch the foreground window's keyboard layout to locale_str.
        Uses AttachThreadInput so ActivateKeyboardLayout affects the right thread.
        Returns True on success.
        """
        hkl = _user32.LoadKeyboardLayoutW(locale_str, _KLF_ACTIVATE)
        if not hkl:
            return False

        hwnd       = _user32.GetForegroundWindow()
        target_tid = _user32.GetWindowThreadProcessId(hwnd, None)
        our_tid    = _kernel32.GetCurrentThreadId()

        if target_tid and target_tid != our_tid:
            _user32.AttachThreadInput(our_tid, target_tid, True)
            _user32.ActivateKeyboardLayout(hkl, 0)
            _user32.AttachThreadInput(our_tid, target_tid, False)
        else:
            _user32.ActivateKeyboardLayout(hkl, 0)

        return True


# ── Unsupported platform ───────────────────────────────────────────────────────
else:
    def detect_hebrew_and_english():
        return None, None

    def switch_to(_locale):
        pass
