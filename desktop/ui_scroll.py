"""Mouse-wheel support for native canvas pages, without stealing table scrolling."""


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
