"""Small native navigation groups over the existing notebook/page contracts."""
import tkinter as tk
from tkinter import ttk


class WorkspaceNavigation:
    def __init__(self,parent,tabs,tracker):
        self.tabs=tabs;self.tracker=tracker;c=tracker.app.colors;app=tracker.app
        style=ttk.Style();style.configure('Workspace.TNotebook',background=c['bg'],borderwidth=0);style.layout('Workspace.TNotebook.Tab',[])
        tabs.configure(style='Workspace.TNotebook')
        self.frame=tk.Frame(parent,bg=c['bg']);self.frame.pack(before=tabs,fill='x',pady=(0,8))
        row=tk.Frame(self.frame,bg=c['bg']);row.pack(fill='x');self.buttons={};self.locations={};self.menus={}
        def destination(label,page):
            self.locations[str(page)]=label
            return lambda:tabs.select(page)
        for label,page in [('Home',tracker.home.frame),('Craft',tracker.craft_tab),('Grind',tracker.grind.frame),('Quests',tracker.guild.frame)]:
            button=app.text_button(row,label.upper(),destination(label,page));button.pack(side='left',padx=(0,6));self.buttons[label]=button
            button.bind('<Leave>',lambda event:self.sync())
        groups=[('Planning',[
            ('Cooking & alchemy calculator',app.open_planner),('CP Info',destination('CP Info',tracker.cp_info.frame)),('Imperial turn-ins',destination('Imperial',tracker.imperial.frame)),('Gear planner',app.open_gear_planner),('Fairy Codex',app.open_fairy)]),
            ('History',[
            ('Recorded loot',destination('Recorded loot',tracker.tree.master)),('Item totals',destination('Item totals',tracker.totals_tree.master)),('Silver value',destination('Silver value',tracker.silver.frame)),('Sessions',destination('Sessions',tracker.insights.sessions_frame)),('Insights',destination('Insights',tracker.insights.frame)),('Big Drops',destination('Big Drops',tracker.big_drops.frame)),('Export loot CSV',tracker.export)]),
            ('Readers',[
            ('Live recognized items',destination('Live recognized items',tracker.visible_tree.master)),('Loot OCR reader',destination('Loot OCR reader',tracker.preview.master)),('Tool OCR reader',app.tool_debug.open),('Quest OCR reader',tracker.guild.reader_view.open),('Saved diagnostics',tracker.open_diagnostics)])]
        for title,entries in groups:
            menu=tk.Menu(row,tearoff=False,bg=c['panel'],fg=c['text'],activebackground=c['violet'],activeforeground=c['text'])
            button=tk.Menubutton(row,text=title.upper()+' ▾',menu=menu,bg=c['panel2'],fg=c['text'],activebackground=c['violet2'],activeforeground=c['text'],font=('Segoe UI Semibold',9),relief='flat',padx=9,pady=7,takefocus=True)
            button.pack(side='left',padx=(0,6));self.menus[title]=menu
            for label,command in entries:menu.add_command(label=label,command=command)
        self.location=tk.StringVar(value='Home');tk.Label(self.frame,textvariable=self.location,bg=c['bg'],fg=c.get('teal',c['bright']),font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(7,0))
        tabs.bind('<<NotebookTabChanged>>',lambda e:self.sync(),add='+')
        self.sync()

    def sync(self):
        page=self.tabs.select();title=self.locations.get(page,'Workspace');self.location.set(title)
        c=self.tracker.app.colors
        for label,button in self.buttons.items():button.configure(bg=c['violet'] if title==label else c['panel2'])
