"""
Input source / keyboard layout switcher.
Mac:     uses Carbon TIS API via objc.loadBundleFunctions (pyobjc, bundled via rumps).
Windows: uses user32 LoadKeyboardLayout + AttachThreadInput via ctypes.
"""

import sys

# ── macOS ──────────────────────────────────────────────────────────────────────
if sys.platform == 'darwin':
    import objc
    from Foundation import NSBundle

    # Load Carbon TIS functions via pyobjc
    _carbon_bundle = NSBundle.bundleWithPath_(
        '/System/Library/Frameworks/Carbon.framework'
    )

    # Define the TIS functions we need
    _tis_funcs = [
        ('TISCopyCurrentKeyboardInputSource', b'@'),
        ('TISCreateInputSourceList', b'@@Z'),
        ('TISSelectInputSource', b'i@'),
        ('TISGetInputSourceProperty', b'@@^{__CFString=}'),
    ]
    _tis = {}
    objc.loadBundleFunctions(_carbon_bundle, _tis, _tis_funcs)

    TISCopyCurrentKeyboardInputSource = _tis['TISCopyCurrentKeyboardInputSource']
    TISCreateInputSourceList = _tis['TISCreateInputSourceList']
    TISSelectInputSource = _tis['TISSelectInputSource']
    TISGetInputSourceProperty = _tis['TISGetInputSourceProperty']

    # Load the kTISPropertyInputSourceID constant
    _tis_constants = {}
    objc.loadBundleVariables(_carbon_bundle, _tis_constants, [
        ('kTISPropertyInputSourceID', b'^{__CFString=}'),
    ])
    kTISPropertyInputSourceID = _tis_constants['kTISPropertyInputSourceID']

    def _get_source_id(source):
        sid = TISGetInputSourceProperty(source, kTISPropertyInputSourceID)
        return str(sid) if sid else ''

    def get_all_source_ids():
        sources = TISCreateInputSourceList(None, False)
        if not sources:
            return []
        return [_get_source_id(sources[i]) for i in range(len(sources))]

    def get_current_source_id():
        source = TISCopyCurrentKeyboardInputSource()
        return _get_source_id(source) if source else ''

    def switch_to(target_id):
        """Switch the active input source to target_id. Returns True on success."""
        sources = TISCreateInputSourceList(None, False)
        if not sources:
            return False
        for i in range(len(sources)):
            source = sources[i]
            if _get_source_id(source) == target_id:
                TISSelectInputSource(source)
                return True
        return False

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
