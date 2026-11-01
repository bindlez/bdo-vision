"""Opt-in, in-memory OCR inspection. No captures, polling or files of its own."""
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class OCRReaderView:
    def __init__(self, app, title, read_now):
        self.app = app
        self.title = title
        self.read_now = read_now
        self.window = None
        self.opened = False
        self.photo = None
        self.generation = 0

    def open(self):
        if self.opened:
            self.window.deiconify()
            self.window.lift()
            return
        c = self.app.colors
        self.window = win = tk.Toplevel(self.app.root)
        win.title('BDO Vision • ' + self.title)
        win.geometry('940x680')
        win.minsize(700, 480)
        win.configure(bg=c['bg'])
        self.opened = True
        self.generation += 1
        win.protocol('WM_DELETE_WINDOW', self.close)
        header = tk.Frame(win, bg=c['bg'], padx=20, pady=16)
        header.pack(fill='x')
        tk.Label(header, text=self.title, bg=c['bg'], fg=c['text'],
                 font=('Segoe UI Semibold', 18)).pack(side='left')
        self.app.action(header, 'READ NOW', self.read_now, primary=True).pack(side='right')
        self.status = tk.StringVar(value='Waiting for the next scan. Return to BDO to expose its labels.')
        tk.Label(win, textvariable=self.status, bg=c['bg'], fg=c['secondary'],
                 wraplength=890, justify='left').pack(fill='x', padx=20, pady=(0, 10))
        self.preview = tk.Label(win, bg=c['panel'], fg=c['muted'], text='No capture yet', height=1)
        self.preview.pack(fill='both', padx=20)
        body = tk.Frame(win, bg=c['bg'])
        body.pack(fill='both', expand=True, padx=20, pady=12)
        self.text = tk.Text(body, wrap='word', bg=c['panel'], fg=c['text'],
                            insertbackground=c['text'], font=('Consolas', 10), relief='flat', state='disabled')
        scroll = ttk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.text.pack(fill='both', expand=True)
        tk.Label(win, text='Actual reader input • kept in memory only while open • closing releases the preview',
                 bg=c['bg'], fg=c['muted'], font=('Segoe UI', 9)).pack(padx=20, pady=(0, 12))

    def token(self):
        """Plain values are safe to consult from a worker; never access Tk there."""
        return self.generation if self.opened else None

    def show(self, token, image, detail, captured=None):
        """Called on the Tk thread. Ignore results from a closed/reopened viewer."""
        if token is None or token != self.token():
            return
        stamp = time.strftime('%H:%M:%S', time.localtime(captured or time.time()))
        self.status.set('Captured ' + stamp + ' • inspect the image and agreement below')
        if image is not None:
            self.photo = ImageTk.PhotoImage(image)
            self.preview.configure(image=self.photo, text='', height=0)
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', str(detail)[:16000])
        self.text.configure(state='disabled')

    def paused(self, reason):
        if self.opened:
            self.status.set('Paused • ' + str(reason)[:240] + ' • image is the previous capture')

    def close(self):
        self.opened = False
        self.generation += 1
        self.photo = None
        if self.window is not None:
            self.window.destroy()
        self.window = None


def preview_image(image):
    result = image.copy()
    result.thumbnail((880, 290), Image.Resampling.LANCZOS)
    return result


def label_montage(crops):
    """Bound diagnostic memory independently of resolution and number of labels."""
    result = Image.new('RGB', (880, 290), '#12101a')
    y = 0
    for crop in crops[:8]:
        tile = crop.copy().convert('RGB')
        tile.thumbnail((880, 32), Image.Resampling.LANCZOS)
        result.paste(tile, (0, y))
        y += 36
    return result
