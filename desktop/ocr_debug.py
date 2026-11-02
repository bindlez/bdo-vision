"""Opt-in, in-memory OCR inspection. No captures, polling or files of its own."""
import time
from collections import deque
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
        self.raw_image=None
        self.events=deque(maxlen=24)
        self.full_window=None
        self.last_pause=None

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
        self.last_pause=None
        self.generation += 1
        win.protocol('WM_DELETE_WINDOW', self.close)
        header = tk.Frame(win, bg=c['bg'], padx=20, pady=16)
        header.pack(fill='x')
        tk.Label(header, text=self.title, bg=c['bg'], fg=c['text'],
                 font=('Segoe UI Semibold', 18)).pack(side='left')
        self.app.action(header, 'READ NOW', self.read_now, primary=True).pack(side='right')
        self.app.action(header, 'FULL IMAGE', self.open_full_image, primary=False).pack(side='right',padx=8)
        self.hold=tk.BooleanVar(value=False)
        tk.Checkbutton(win,text='Hold this capture while new scans continue',variable=self.hold,bg=c['bg'],fg=c['text'],selectcolor=c['panel']).pack(anchor='w',padx=20)
        self.status = tk.StringVar(value='Waiting for the next scan. Return to BDO to expose its labels.')
        tk.Label(win, textvariable=self.status, bg=c['bg'], fg=c['secondary'],
                 wraplength=890, justify='left').pack(fill='x', padx=20, pady=(0, 10))
        self.preview = tk.Label(win, bg=c['panel'], fg=c['muted'], text='No capture yet', height=1)
        self.preview.pack(fill='both', padx=20)
        tabs=ttk.Notebook(win);tabs.pack(fill='both',expand=True,padx=20,pady=12)
        body = tk.Frame(tabs, bg=c['bg']);tabs.add(body,text='OCR reading / detection')
        self.text = tk.Text(body, wrap='word', bg=c['panel'], fg=c['text'],
                            insertbackground=c['text'], font=('Consolas', 10), relief='flat', state='disabled')
        scroll = ttk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.text.pack(fill='both', expand=True)
        self.history=tk.Text(tabs,bg=c['panel'],fg=c['text'],font=('Consolas',10),wrap='word',state='disabled')
        tabs.add(self.history,text='Attempt history')
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
        self.log('Captured '+stamp+' · '+str(detail).split('\n')[0][:180])
        if self.hold.get():return
        self.status.set('Captured ' + stamp + ' • inspect the image and agreement below')
        self.last_pause=None
        if image is not None:
            self.raw_image=source_image(image)
            self.photo = ImageTk.PhotoImage(preview_image(image))
            self.preview.configure(image=self.photo, text='', height=0)
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', str(detail)[:16000])
        self.text.configure(state='disabled')

    def paused(self, reason):
        if self.opened:
            if self.last_pause==str(reason):return
            self.last_pause=str(reason)
            self.status.set('Paused • ' + str(reason)[:240] + ' • image is the previous capture')
            self.log('PAUSED / NOT ACCEPTED: '+str(reason))
            old=self.text.get('1.0','end')[:8000]
            self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('1.0',('LATEST STATUS: '+str(reason)+'\nPrevious recognition follows:\n'+old)[:16000]);self.text.configure(state='disabled')

    def log(self,message):
        if self.events and self.events[-1][1]==message:return
        self.events.append((time.strftime('%H:%M:%S'),message))
        self.history.configure(state='normal');self.history.delete('1.0','end')
        self.history.insert('1.0','\n\n'.join(at+'  '+msg for at,msg in reversed(self.events)))
        self.history.configure(state='disabled')

    def open_full_image(self):
        if self.raw_image is None:
            self.paused('No capture yet. READ NOW, then return to BDO for the scan.');return
        if self.full_window is not None and self.full_window.winfo_exists():self.full_window.destroy()
        win=self.full_window=tk.Toplevel(self.window);win.title('OCR source image · scroll to inspect');win.geometry('1000x650')
        canvas=tk.Canvas(win,bg='#100d18');canvas.grid(row=0,column=0,sticky='nsew')
        x=ttk.Scrollbar(win,orient='horizontal',command=canvas.xview);x.grid(row=1,column=0,sticky='ew')
        y=ttk.Scrollbar(win,orient='vertical',command=canvas.yview);y.grid(row=0,column=1,sticky='ns')
        canvas.configure(xscrollcommand=x.set,yscrollcommand=y.set)
        win.rowconfigure(0,weight=1);win.columnconfigure(0,weight=1)
        canvas.photo=ImageTk.PhotoImage(self.raw_image);canvas.create_image(0,0,image=canvas.photo,anchor='nw');canvas.configure(scrollregion=canvas.bbox('all'))

    def close(self):
        self.opened = False
        self.generation += 1
        self.photo = None
        self.raw_image=None;self.events.clear();self.full_window=None
        if self.window is not None:
            self.window.destroy()
        self.window = None


def preview_image(image):
    result = image.copy()
    result.thumbnail((880, 290), Image.Resampling.LANCZOS)
    return result


def source_image(image):
    result=image.copy();result.thumbnail((1920,1080),Image.Resampling.LANCZOS);return result


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
