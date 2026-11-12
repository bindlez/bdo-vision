"""Show saved game areas without changing the current capture settings."""
import tkinter as tk


def show_layout_map(parent, bounds, layout, colors):
    window = tk.Toplevel(parent)
    window.title('BDO Vision · UI map')
    window.configure(bg=colors['bg'])
    canvas_width = 640
    _, left, top, right, bottom = bounds
    width, height = right - left, bottom - top
    canvas_height = max(180, round(canvas_width * height / width))
    canvas = tk.Canvas(window, width=canvas_width, height=canvas_height,
                       bg=colors['panel'], highlightthickness=0)
    canvas.pack(padx=16, pady=(16, 8))
    areas = [('item_log', 'Item Log', '#46d8c6'),
             ('rare_log', 'Rare Item Log', '#d9ab56'),
             ('text_feed', 'Personal loot feed', '#76b6ff'),
             ('quest_widget', 'Quest widget', '#bc91f2'),
             ('minimap', 'Minimap', '#a5d878')]
    status = tk.StringVar(master=window)
    tk.Label(window, textvariable=status, bg=colors['bg'], fg=colors['text'],
             wraplength=640, justify='left').pack(anchor='w', padx=16, pady=(0, 8))
    tk.Label(window, text='Save changes in BDO Edit UI. Positions update from the saved layout.',
             bg=colors['bg'], fg=colors['muted'], wraplength=640, justify='left').pack(anchor='w', padx=16, pady=(0, 16))

    def render(current_bounds, current_layout):
        nonlocal canvas_height
        _, x_left, y_top, x_right, y_bottom = current_bounds
        w_game, h_game = x_right - x_left, y_bottom - y_top
        new_height = max(180, round(canvas_width * h_game / w_game))
        if new_height != canvas_height:
            canvas_height = new_height
            canvas.configure(height=canvas_height)
        canvas.delete('all')
        labels = []
        for key, label, color in areas:
            box = current_layout.get(key)
            if not box:
                labels.append(label + ' · unavailable')
                continue
            x, y, w, h = box
            x1, y1 = (x - x_left) * canvas_width / w_game, (y - y_top) * canvas_height / h_game
            x2, y2 = (x + w - x_left) * canvas_width / w_game, (y + h - y_top) * canvas_height / h_game
            canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
            canvas.create_text(x1 + 4, y1 + 4, text=label, anchor='nw', fill=color)
            labels.append(label + ' · found')
        status.set('   |   '.join(labels))

    previous = [bounds, layout]

    def refresh():
        from loot_layout import find_saved_layout
        from windows_bdo import visible_bdo_capture_bounds
        try:
            current_bounds = visible_bdo_capture_bounds()
            current_layout = find_saved_layout(current_bounds)
            if [current_bounds, current_layout] != previous:
                render(current_bounds, current_layout)
                previous[:] = [current_bounds, current_layout]
        except (OSError, ValueError):
            canvas.delete('all')
            status.set('Waiting for a visible game and saved layout.')
            previous[:] = [None, None]
        window.after(1000, refresh)

    render(bounds, layout)
    window.after(1000, refresh)
    return window
