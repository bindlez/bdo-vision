"""Windows-only, user-triggered BDO window helpers.

Never send input unless a BDO window is actually foreground. No process
injection, memory reads, global key hook, or anti-cheat interaction.
"""
import ctypes
from ctypes import wintypes

GAME_EXE_HINTS = ('blackdesert64', 'blackdesert32', 'blackdesertonline', 'blackdesert.exe')


def _user32():
    user32 = ctypes.windll.user32
    # Declare pointer-sized Win32 handles correctly on 64-bit Windows.
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    return user32


def _process_name(hwnd):
    user32 = _user32()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ''
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    process = kernel.OpenProcess(0x1000, False, pid.value)
    if not process:
        return ''
    try:
        buf = ctypes.create_unicode_buffer(2048)
        length = wintypes.DWORD(len(buf))
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
        if kernel.QueryFullProcessImageNameW(process, 0, buf, ctypes.byref(length)):
            return buf.value.rsplit('\\', 1)[-1].lower()
        return ''
    finally:
        kernel.CloseHandle(process)


def is_bdo_window(hwnd):
    if not hwnd:
        return False
    exe = _process_name(hwnd)
    if exe:
        return any(hint in exe for hint in GAME_EXE_HINTS) and 'launcher' not in exe
    # Only fall back to window title when the game's executable is inaccessible.
    # Browsers may display 'Black Desert' in their tab/window title.
    title_buf = ctypes.create_unicode_buffer(512)
    _user32().GetWindowTextW(hwnd, title_buf, len(title_buf))
    title = title_buf.value.lower().strip()
    return ('black desert' in title or 'blackdesert' in title) and 'launcher' not in title


def is_bdo_foreground():
    """OCR foreground check (may use title if process query is inaccessible)."""
    return is_bdo_window(_user32().GetForegroundWindow())


def item_regions_visible(regions):
    """Allow read-only screen OCR behind our UI only for uncovered game regions.

    This never changes keyboard/tray foreground requirements.
    """
    try:
        user32=_user32()
        user32.WindowFromPoint.argtypes=[wintypes.POINT]
        user32.WindowFromPoint.restype=wintypes.HWND
        user32.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
        user32.GetAncestor.restype=wintypes.HWND
        windows=[h for h in find_bdo_windows() if user32.IsWindowVisible(h) and not user32.IsIconic(h)]
        if not windows:return False,'BDO must be visible, not minimized or in the tray'
        if not regions:return False,'Select an item capture area'
        for x,y,width,height in regions:
            if width<8 or height<8:return False,'Select a larger item capture area'
            corners=[(x+2,y+2),(x+width-3,y+height-3)]
            game=next((h for h in windows if _contains_region(user32,h,x,y,width,height)),None)
            if not game:return False,'Capture area is outside the visible BDO window'
            points=corners+[(px,py) for px in range(x+3,x+width,24) for py in range(y+3,y+height,24)]
            for px,py in points:
                top=user32.GetAncestor(user32.WindowFromPoint(wintypes.POINT(px,py)),2)
                if top!=game:return False,'Item area is covered by '+(_process_name(top) or 'another window')+'; move it aside'
        return True,'Item areas visible'
    except Exception:
        return False,'Unable to verify the visible BDO item area'


def _contains_region(user32,hwnd,x,y,width,height):
    rect=wintypes.RECT()
    return bool(user32.GetWindowRect(hwnd,ctypes.byref(rect)) and rect.left<=x and rect.top<=y and rect.right>=x+width and rect.bottom>=y+height)


def is_verified_bdo_foreground():
    """Strict check for sending keys: never trust a matching browser title."""
    hwnd = _user32().GetForegroundWindow()
    exe = _process_name(hwnd).lower() if hwnd else ''
    return bool(exe and 'launcher' not in exe and
                any(hint in exe for hint in GAME_EXE_HINTS))


def find_bdo_windows():
    user32 = _user32()
    CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    handles = []
    def collect(hwnd, _):
        if is_bdo_window(hwnd):
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
            if area > 30000:
                handles.append((bool(user32.IsWindowVisible(hwnd)), area, hwnd))
        return True
    user32.EnumWindows.argtypes = [CALLBACK, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.EnumWindows(CALLBACK(collect), 0)
    handles.sort(reverse=True)
    return [h for _, _, h in handles]


def restore_bdo():
    """Restore an ordinary minimized or background game window (NOT native tray mode)."""
    try:
        windows = [h for h in find_bdo_windows() if _user32().IsWindowVisible(h)]
        if not windows:
            return False, 'No ordinary BDO window found. If BDO is in the tray, use SUPER RESTORE.'
        hwnd = windows[0]
        user32 = _user32()
        # Restore regular minimized windows; never force-show a tray-hidden game.
        user32.ShowWindow(hwnd, 9)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        if user32.IsWindowVisible(hwnd):
            return True, 'BDO window restored or brought forward.'
        return False, 'Normal restore did not work. Try SUPER RESTORE for native tray mode.'
    except Exception as exc:
        return False, 'Restore failed: ' + str(exc)


def send_ctrl_v_if_bdo_foreground():
    """Only sends the user-selected tray shortcut to the foreground BDO window."""
    if not is_verified_bdo_foreground():
        return False, 'BDO was not verified in front after 2 seconds. Ctrl+V cancelled.'
    # Ctrl+V is the user-configured tray hotkey. Confirm the BDO keybind; elsewhere this would paste.
    # SendInput is preferable to keybd_event and never changes clipboard contents.
    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD),
                    ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD),
                    ('dwExtraInfo', ULONG_PTR)]
    class INPUTUNION(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT)]
    class INPUT(ctypes.Structure):
        _fields_ = [('type', wintypes.DWORD), ('u', INPUTUNION)]
    presses = ((0x11, 0), (0x56, 0), (0x56, 2), (0x11, 2))
    seq = (INPUT * 4)(*[INPUT(1, INPUTUNION(KEYBDINPUT(code, 0, flag, 0, 0))) for code, flag in presses])
    user32 = _user32()
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    count = user32.SendInput(4, seq, ctypes.sizeof(INPUT))
    if count != 4:
        # Best-effort release if Windows accepted only part of the sequence.
        releases = (INPUT * 2)(INPUT(1, INPUTUNION(KEYBDINPUT(0x56, 0, 2, 0, 0))),
                               INPUT(1, INPUTUNION(KEYBDINPUT(0x11, 0, 2, 0, 0))))
        user32.SendInput(2, releases, ctypes.sizeof(INPUT))
        return False, 'Ctrl+V was not fully delivered. Try matching the privilege level of BDO.'
    return True, 'Ctrl+V keystrokes delivered to verified foreground BDO; checking tray state…'


def inspect_bdo_visibility():
    """Report whether the real game process has a visible window.

    This cannot prove BDO entered its own tray mode; only BDO can confirm that.
    Returns 'visible', 'hidden', or 'unknown'.
    """
    try:
        user32 = _user32()
        windows = [hwnd for hwnd in find_bdo_windows()
                   if any(hint in _process_name(hwnd) for hint in GAME_EXE_HINTS)]
        if not windows:
            return 'unknown'
        if any(user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd) for hwnd in windows):
            return 'visible'
        return 'hidden'
    except Exception:
        return 'unknown'


def _is_bdo_tray_label(label):
    """Be conservative; never click a different program's notification icon."""
    import re
    name = str(label or '').strip().lower()
    if not name or any(word in name for word in ('vision', 'launcher', 'patcher', 'updater')):
        return False
    return bool('black desert' in name or 'blackdesert' in name or
                'black spirit' in name or
                re.match(r'^bdo(?:\b|\s|\.)', name))


def _matching_tray_buttons(container):
    """Use Windows UI Automation labels instead of hard-coded screen pixels."""
    if not container:
        return []
    try:
        controls = []
        for kind in ('Button', 'ListItem', 'MenuItem'):
            try: controls.extend(container.descendants(control_type=kind))
            except Exception: pass
    except Exception:
        return []
    matches = []
    for button in controls:
        try:
            if _is_bdo_tray_label(button.window_text()):
                matches.append(button)
        except Exception:
            continue
    return matches


def _bdo_window_visible():
    try:
        user32 = _user32()
        return (is_verified_bdo_foreground() or
                any(bool(user32.IsWindowVisible(hwnd)) and not bool(user32.IsIconic(hwnd))
                    for hwnd in find_bdo_windows()))
    except Exception:
        return False


def _click_bdo_tray_icon(button):
    """Return true only after a BDO window reappears; never infer from a click."""
    import time
    def wait_until_visible(seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if _bdo_window_visible():
                return True
            time.sleep(.35)
        return _bdo_window_visible()

    try:
        button.click_input()
        if wait_until_visible(5):
            return True
        button.double_click_input()
        return wait_until_visible(5)
    except Exception:
        return False


def _find_tray_icons(desktop):
    """Search both visible taskbar and Explorer overflow using stable UIA labels.

    Avoid fixed screen coordinates and never click unidentified tray icons.
    """
    containers = []
    try:
        containers.append(desktop.window(class_name='Shell_TrayWnd'))
    except Exception:
        pass
    try:
        for win in desktop.windows():
            try:
                cls = (win.class_name() or '').lower()
                title = (win.window_text() or '').lower()
                if ('notifyiconoverflowwindow' in cls or 'overflowxaml' in cls or
                    'notification overflow' in title or 'hidden icons' in title):
                    containers.append(win)
            except Exception:
                continue
    except Exception:
        pass
    matches=[]
    seen=set()
    for container in containers:
        for icon in _matching_tray_buttons(container):
            try:
                ident = icon.element_info.handle or id(icon)
            except Exception:
                ident=id(icon)
            if ident not in seen:
                matches.append(icon);seen.add(ident)
    return matches


def _reveal_hidden_icons(desktop):
    """Ask Explorer to reveal notification overflow; supports Win10/Win11 UIA labels."""
    try:
        taskbar=desktop.window(class_name='Shell_TrayWnd')
        for control in taskbar.descendants(control_type='Button'):
            label=(control.window_text() or '').lower()
            if any(needle in label for needle in ('notification chevron', 'show hidden icons', 'hidden icons')):
                control.click_input()
                return True
    except Exception:
        pass
    return False


def super_restore_bdo():
    """Activate BDO's *own* tray icon and check the game window reappeared.

    Works best when Windows exposes the BDO notification icon through UIA.
    Never ShowWindow() a tray-hidden game as a substitute: that doesn't exit BDO
    native low-resource mode. Does not claim success on mere mouse clicks.
    """
    import time
    if _bdo_window_visible():
        return restore_bdo()
    initialized=False
    try:
        import comtypes
        comtypes.CoInitialize()
        initialized=True
        from pywinauto import Desktop
    except ImportError:
        return False, 'Install tray support once using INSTALL-TRAY-SUPPORT.bat.'
    try:
        desktop=Desktop(backend='uia')
        icons=_find_tray_icons(desktop)
        for icon in icons:
            if _click_bdo_tray_icon(icon):
                return True, 'BDO restored through its notification-area icon.'
        _reveal_hidden_icons(desktop)
        time.sleep(.4)
        icons=_find_tray_icons(desktop)
        for icon in icons:
            if _click_bdo_tray_icon(icon):
                return True, 'BDO restored through its hidden notification-area icon.'
        return False, ('BDO tray icon was not accessible to Windows UI Automation. '
                       'Click the BDO/Black Spirit icon beside the Windows clock, '
                       'possibly under Show hidden icons (^).')
    except Exception as exc:
        return False, 'Super Restore could not access Windows notification area: '+str(exc)
    finally:
        if initialized:
            try: comtypes.CoUninitialize()
            except Exception: pass
