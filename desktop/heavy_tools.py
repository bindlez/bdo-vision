"""Local screenshot review, loaded only in the Tier −1 child process."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from heavy_tools_launcher import LAB_TITLE


IMAGE_TYPES = [('Images', '*.png *.jpg *.jpeg *.bmp')]


def load_image(path):
    with Image.open(path) as source:
        if source.width * source.height > 25_000_000:
            raise ValueError('Use an image under 25 megapixels.')
        return ImageOps.exif_transpose(source).convert('RGB')


def slot_boxes(rect, rows, columns):
    left, top, right, bottom = rect
    width, height = right - left, bottom - top
    if not (rows > 0 and columns > 0 and rows * columns <= 240):
        raise ValueError('Use 1–240 slots.')
    if width < columns * 8 or height < rows * 8:
        raise ValueError('Select at least 8 × 8 source pixels per slot.')
    xs = [left + round(i * width / columns) for i in range(columns + 1)]
    ys = [top + round(i * height / rows) for i in range(rows + 1)]
    return [(xs[c], ys[r], xs[c + 1], ys[r + 1]) for r in range(rows) for c in range(columns)]


def icon_key(image):
    # Exact match after resizing the central icon area. Borders and labels can vary.
    dx, dy = image.width // 8, image.height // 8
    return image.crop((dx, dy, image.width - dx, image.height - dy)).resize(
        (24, 24), Image.Resampling.LANCZOS).tobytes()


def match_label(labels):
    if not labels:
        return 'Unknown'
    if len(labels) > 1:
        return 'Ambiguous · ' + ', '.join(sorted(labels))
    return next(iter(labels))


class ScreenshotLab:
    def __init__(self, root):
        self.root = root
        self.image = self.selection = None
        self.boxes = []
        self.references = {}
        self.rows = tk.StringVar(value='1')
        self.columns = tk.StringVar(value='1')
        self.status = tk.StringVar(value='Open a screenshot, then drag around one gear slot or an evenly spaced inventory grid.')

        root.title(LAB_TITLE)
        root.configure(bg='#141b23')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', background='#141b23', foreground='#e3eff5', font=('Segoe UI', 10))
        style.configure('TButton', background='#253845', padding=(10, 5))
        style.map('TButton', background=[('active', '#315361')])
        style.configure('TEntry', fieldbackground='#1d2c36', insertcolor='#e3eff5')
        frame = ttk.Frame(root, padding=14)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Screenshot Lab', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Review gear and inventory icons from local screenshots.').pack(anchor='w', pady=(0, 12))
        controls = ttk.Frame(frame)
        controls.pack(fill='x')
        ttk.Button(controls, text='Open screenshot', command=self.open_screenshot).pack(side='left', padx=(0, 8))
        ttk.Button(controls, text='Load reference icons', command=self.open_references).pack(side='left', padx=(0, 10))
        for name, value in [('Rows', self.rows), ('Columns', self.columns)]:
            ttk.Label(controls, text=name).pack(side='left', padx=(6, 3))
            ttk.Entry(controls, textvariable=value, width=4).pack(side='left')
        ttk.Button(controls, text='Review slots', command=self.review).pack(side='left', padx=(10, 0))

        content = ttk.Frame(frame)
        content.pack(fill='both', expand=True, pady=10)
        self.canvas = tk.Canvas(content, width=650, height=400, bg='#0b121a', highlightthickness=0)
        self.canvas.pack(side='left', anchor='nw')
        self.canvas.bind('<ButtonPress-1>', self.start_selection)
        self.canvas.bind('<B1-Motion>', self.update_selection)
        self.canvas.bind('<ButtonRelease-1>', self.update_selection)

        sidebar = ttk.Frame(content, padding=(10, 0, 0, 0))
        sidebar.pack(side='left', fill='both', expand=True)
        self.preview = ttk.Label(sidebar, text='Slot preview')
        self.preview.pack(anchor='w', pady=(0, 6))
        results = ttk.Frame(sidebar)
        results.pack(fill='both', expand=True)
        self.results = tk.Listbox(results, width=24, bg='#0b121a', fg='#e3eff5',
                                  selectbackground='#315361', relief='flat', exportselection=False)
        scroll = ttk.Scrollbar(results, orient='vertical', command=self.results.yview)
        self.results.configure(yscrollcommand=scroll.set)
        self.results.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.results.bind('<<ListboxSelect>>', self.show_slot)
        ttk.Label(frame, textvariable=self.status, wraplength=830).pack(anchor='w')

    def open_screenshot(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=IMAGE_TYPES)
        if not path:
            return
        try:
            image = load_image(path)
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            messagebox.showerror(LAB_TITLE, str(exc), parent=self.root)
            return
        self.image = image
        thumbnail = image.copy()
        thumbnail.thumbnail((650, 400))
        self.photo = ImageTk.PhotoImage(thumbnail)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
        self.selection = None
        self.clear_results()
        self.status.set('Drag around the icon or grid. Set rows and columns, then choose Review slots.')

    def start_selection(self, event):
        if self.image is not None:
            self.start = self.canvas_point(event)
            self.clear_results()
            self.update_selection(event)

    def canvas_point(self, event):
        return min(max(0, event.x), self.photo.width()), min(max(0, event.y), self.photo.height())

    def update_selection(self, event):
        if self.image is None or not hasattr(self, 'start'):
            return
        x, y = self.canvas_point(event)
        left, right = sorted((self.start[0], x))
        top, bottom = sorted((self.start[1], y))
        self.selection = left, top, right, bottom
        self.canvas.delete('selection')
        self.canvas.create_rectangle(*self.selection, outline='#61e8d2', width=2, tags='selection')

    def clear_results(self):
        self.boxes = []
        self.results.delete(0, 'end')
        self.preview.configure(image='', text='Slot preview')
        self.slot_photo = None

    def open_references(self):
        paths = filedialog.askopenfilenames(parent=self.root, filetypes=IMAGE_TYPES,
                                           title='Choose cropped icons named after their items')
        if not paths:
            return
        references = {}
        try:
            for path in paths:
                key = icon_key(load_image(path))
                references.setdefault(key, set()).add(Path(path).stem)
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            messagebox.showerror(LAB_TITLE, str(exc), parent=self.root)
            return
        self.references = references
        if self.boxes:
            self.review()
        else:
            self.status.set(f'Loaded {len(paths)} references. Choose Review slots after selecting an area.')

    def review(self):
        if self.selection is None:
            self.status.set('Drag a selection on a screenshot first.')
            return
        left, top, right, bottom = self.selection
        sx = self.image.width / self.photo.width()
        sy = self.image.height / self.photo.height()
        rect = (round(left * sx), round(top * sy), round(right * sx), round(bottom * sy))
        try:
            boxes = slot_boxes(rect, int(self.rows.get()), int(self.columns.get()))
        except ValueError:
            self.status.set('Enter whole numbers for 1–240 slots, each at least 8 × 8 source pixels.')
            return
        self.clear_results()
        self.boxes = boxes
        for index, box in enumerate(boxes, start=1):
            labels = self.references.get(icon_key(self.image.crop(box)))
            self.results.insert('end', f'{index:02d}  {match_label(labels)}')
        self.results.selection_set(0)
        self.show_slot()
        self.status.set(f'{len(boxes)} slots · Exact icon matches only. Quantities and enhancement are unverified.')

    def show_slot(self, _event=None):
        selected = self.results.curselection()
        if selected and self.boxes:
            slot = self.image.crop(self.boxes[selected[0]])
            slot.thumbnail((70, 70))
            self.slot_photo = ImageTk.PhotoImage(slot)
            self.preview.configure(image=self.slot_photo, text='')


def run():
    root = tk.Tk()
    ScreenshotLab(root)
    root.mainloop()
