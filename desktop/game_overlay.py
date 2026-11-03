"""Shared native overlay chrome: passive Windows surfaces, saved snapping, no OCR."""
import ctypes
from ctypes import wintypes
import tkinter as tk
from overlay_layout import preferences, dock, snap, tile

INK = '#0c0b13'
PANEL = '#151320'
LINE = '#393047'
TEXT = '#f5f0ff'
MUTED = '#b3aac6'
VIOLET = '#b39aff'
TEAL = '#70e3d0'
GOLD = '#ffcf83'


def native_handle(win):
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    return user32.GetAncestor(win.winfo_id(), 2)


def passive(win, locked=False):
    """Only our own HWND; never activate or hook BDO. Fail closed on Windows."""
    try:
        win.update_idletasks();user32 = ctypes.windll.user32;handle = native_handle(win)
        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        user32.SetWindowLongW.restype = ctypes.c_long
        style = user32.GetWindowLongW(handle, -20)
        style = (style | 0x08000000 | 0x00000080) & ~0x00000020  # NOACTIVATE / TOOLWINDOW
        if locked:style |= 0x00000020 | 0x00080000  # TRANSPARENT / LAYERED
        user32.SetWindowLongW(handle, -20, style)
        actual = user32.GetWindowLongW(handle, -20)
        return bool(actual & 0x08000000) and (not locked or bool(actual & 0x00000020))
    except (AttributeError, OSError, tk.TclError):return False


def work_area(win):
    """Monitor containing our window, including negative coordinates and taskbar."""
    try:
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT), ('work', wintypes.RECT), ('flags', wintypes.DWORD)]
        user32 = ctypes.windll.user32
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        data = MonitorInfo();data.size = ctypes.sizeof(data)
        if user32.GetMonitorInfoW(user32.MonitorFromWindow(native_handle(win), 2), ctypes.byref(data)):
            r = data.work;return (r.left, r.top, r.right, r.bottom)
    except (AttributeError, OSError, tk.TclError):pass
    return (0, 0, win.winfo_screenwidth(), win.winfo_screenheight())


def geometry(win, rect):
    x, y, w, h = [int(n) for n in rect]
    # Tk interprets negative geometry offsets relative to the right/bottom edge.
    # Set size through Tk, then the absolute virtual-desktop position with Win32.
    win.geometry(f'{w}x{h}+{max(0,x)}+{max(0,y)}')
    try:
        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.SetWindowPos(native_handle(win), None, x, y, w, h, 0x0010 | 0x0004)  # NOACTIVATE / NOZORDER
    except (AttributeError, OSError):pass


class OverlaySurface:
    def __init__(self, root, title, size, options, moved=None):
        self.options = preferences(options);self.size = size;self.moved = moved
        self.window = tk.Toplevel(root, takefocus=False);self.window.withdraw()
        self.window.title(title);self.window.overrideredirect(True)
        self.window.attributes('-topmost', True);self.window.configure(bg=LINE)
        # Slight translucency is static. No idle fade, pulse or frame loop.
        self.window.attributes('-alpha', .97)
        self.body = tk.Frame(self.window, bg=INK);self.body.pack(fill='both', expand=True, padx=1, pady=1)
        self.rect = None;self.drag = None;self.feedback = None

    def place(self, obstacle=None):
        p = self.options
        if p.get('position'):
            geometry(self.window, (*p['position'], *self.size));self.window.update_idletasks()
        area = work_area(self.window)
        self.rect = tile(self.size, area, obstacle, p['corner']) if obstacle else dock(self.size, area, p['corner'], p.get('position'))
        geometry(self.window, self.rect)

    def show(self):
        if not passive(self.window, self.options['locked']):self.window.destroy();return False
        self.window.deiconify();return True

    def draggable(self, *widgets):
        for widget in widgets:
            widget.configure(cursor='fleur' if not self.options['locked'] else 'arrow')
            widget.bind('<ButtonPress-1>', self.press);widget.bind('<B1-Motion>', self.move);widget.bind('<ButtonRelease-1>', self.release)

    def press(self, event):
        if not self.options['locked']:self.drag = (event.x_root, event.y_root, self.rect[0], self.rect[1])

    def move(self, event):
        if self.drag:
            sx, sy, x, y = self.drag;self.rect = (x+event.x_root-sx, y+event.y_root-sy, *self.size)
            geometry(self.window, self.rect)
            target, corner = snap(self.rect, work_area(self.window))
            near = target != self.rect or corner != 'custom'
            self.window.configure(bg=TEAL if near else LINE)
            if self.feedback:self.feedback(('RELEASE TO DOCK · '+corner.replace('-', ' ').upper()) if near and corner!='custom' else 'RELEASE TO SNAP TO EDGE' if near else 'DRAG · EDGES SNAP')

    def release(self, event):
        if self.drag:
            self.drag = None;self.rect, corner = snap(self.rect, work_area(self.window));geometry(self.window, self.rect)
            self.options.update(corner=corner, position=list(self.rect[:2]))
            self.window.configure(bg=LINE)
            if self.feedback:self.feedback('◇  VISION / GRIND')
            if self.moved:self.moved(self.options)

    def close(self):
        if self.window.winfo_exists():self.window.destroy()


def label(parent, text='', size=10, color=TEXT, **kwargs):
    return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color,
                    font=('Segoe UI Semibold' if size >= 10 else 'Segoe UI', size), **kwargs)


def button(parent, text, command, color=MUTED):
    return tk.Button(parent, text=text, command=command, bg=parent.cget('bg'), fg=color,
                     activebackground=LINE, activeforeground=TEXT, relief='flat', bd=0,
                     font=('Segoe UI', 9), padx=7, pady=2, takefocus=False, cursor='hand2')
