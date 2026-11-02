"""Mouse-wheel support for native canvas pages, without stealing table scrolling."""
import tkinter as tk
from tkinter import ttk


def notebook_page(notebook, title, colors):
    """Return the selectable tab and its scrollable content as distinct frames."""
    outer = tk.Frame(notebook, bg=colors['bg'])
    notebook.add(outer, text=title)
    canvas = tk.Canvas(outer, bg=colors['bg'], highlightthickness=0, takefocus=True)
    scrollbar = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
    scrollbar.pack(side='right', fill='y')
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(fill='both', expand=True)
    content = tk.Frame(canvas, bg=colors['bg'], padx=12, pady=10)
    item = canvas.create_window(0, 0, window=content, anchor='nw')
    content.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
    canvas.bind('<Next>', lambda event: canvas.yview_scroll(1, 'pages'))
    canvas.bind('<Prior>', lambda event: canvas.yview_scroll(-1, 'pages'))
    enable_page_wheel(canvas)
    outer.page_canvas = canvas
    outer.page_content = content
    return outer, content


def enable_page_wheel(canvas):
    def scroll(event):
        widget = event.widget
        inside = widget == canvas or str(widget).startswith(str(canvas) + '.')
        if not inside or not event.delta:
            return
        # These controls already implement their own scrolling/selection.
        if widget.winfo_class() in ('Treeview', 'Text', 'Listbox', 'TCombobox', 'TScrollbar'):
            return
        if canvas.yview() == (0.0, 1.0):
            return
        direction = -1 if event.delta > 0 else 1
        canvas.yview_scroll(direction * max(1, abs(event.delta) // 120) * 3, 'units')
        return 'break'

    # A toplevel bind receives events over page labels/buttons as well as blank
    # canvas space. The ancestry check keeps other pages and windows untouched.
    canvas.winfo_toplevel().bind('<MouseWheel>', scroll, add='+')
