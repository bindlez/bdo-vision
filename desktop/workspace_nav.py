"""Visible two-row navigation over the original pages; no destination menus."""
import tkinter as tk
from tkinter import ttk


class WorkspaceNavigation:
    def __init__(self,parent,tabs,tracker):
        self.tabs=tabs;self.tracker=tracker;c=tracker.app.colors;app=tracker.app
        style=ttk.Style();style.configure('Workspace.TNotebook',background=c['bg'],borderwidth=0);style.layout('Workspace.TNotebook.Tab',[])
        tabs.configure(style='Workspace.TNotebook')
        self.frame=tk.Frame(parent,bg=c['bg']);self.frame.pack(before=tabs,fill='x',pady=(0,8))
        row=tk.Frame(self.frame,bg=c['bg']);row.pack(fill='x')
        self.buttons={};self.locations={};self.groups={};self.destination_buttons=[];self.group='Home';self.last_page=None
        def destination(label,page):
            self.locations[str(page)]=label
            return lambda:tabs.select(page)
        primary=[('Home',tracker.home.frame),('Craft',tracker.craft_tab),('Grind',tracker.grind.frame),('Quests',tracker.guild.frame)]
        self.primary={name:destination(name,page) for name,page in primary}
        self.groups={
            'Planning':[
                ('Crafting website',app.open_planner),('CP Info / website',lambda:app.open_planning_page('cp')),
                ('Imperial / website',lambda:app.open_planning_page('imperial')),('CP desktop',destination('CP Info',tracker.cp_info.frame)),
                ('Imperial desktop',destination('Imperial',tracker.imperial.frame)),('Gear planner',app.open_gear_planner),('Fairy Codex website',app.open_fairy),('Fairy desktop',app.open_fairy_desktop)],
            'History':[
                ('Recorded loot',destination('Recorded loot',tracker.tree.master)),('Item totals',destination('Item totals',tracker.totals_tree.master)),
                ('Silver value',destination('Silver value',tracker.silver.frame)),('Sessions',destination('Sessions',tracker.insights.sessions_frame)),
                ('Insights',destination('Insights',tracker.insights.frame)),('Big Drops',destination('Big Drops',tracker.big_drops.frame)),('Export loot CSV',tracker.export)],
            'Readers':[
                ('Live recognized items',destination('Live recognized items',tracker.visible_tree.master)),('Loot OCR reader',destination('Loot OCR reader',tracker.preview.master)),
                ('Tool OCR reader',app.tool_debug.open),('Quest OCR reader',tracker.guild.reader_view.open),('Saved diagnostics',tracker.open_diagnostics),('Inventory reader',app.inventory.debug.open)]}
        self.groups['Home']=[('OPEN CRAFTING WEBSITE',app.open_planner),('CP Info',lambda:app.open_planning_page('cp')),('Scan tool + quest',app.rescan_tools),('Live overlay',tracker.grind.live.open)]
        self.groups['Craft']=[('OPEN CRAFTING WEBSITE',app.open_planner),('Scan tool + quest',app.rescan_tools),('CP Info',lambda:app.open_planning_page('cp')),('Imperial turn-ins',lambda:app.open_planning_page('imperial')),('Tool reader debug',app.tool_debug.open),('Craft overlay',lambda:(tracker.grind.live.open(),tracker.grind.live.craft_panel.open())),('Read inventory',app.inventory.read_delayed),('Toggle I-key snapshots',app.inventory.toggle)]
        self.groups['Grind']=[('Live overlay',tracker.grind.live.open),('Overlay settings',tracker.grind.live.settings),('Big Drops',destination('Big Drops',tracker.big_drops.frame)),('Loot reader debug',self.groups['Readers'][1][1])]
        self.groups['Quests']=[('Scan tool + quest',app.rescan_tools),('Quest reader debug',tracker.guild.reader_view.open),('Quest reminders',self.primary['Quests'])]
        for title in ('Home','Craft','Grind','Quests','Planning','History','Readers'):
            button=app.text_button(row,title.upper(),lambda name=title:self.choose(name));button.pack(side='left',padx=(0,7));self.buttons[title]=button
        self.destinations=tk.Frame(self.frame,bg=c['panel']);self.destinations.pack(fill='x',pady=(5,0))
        self.location=tk.StringVar(value='Home');tk.Label(self.frame,textvariable=self.location,bg=c['bg'],fg=c.get('teal',c['bright']),font=('Segoe UI Semibold',9)).pack(anchor='w',pady=(5,0))
        tabs.bind('<<NotebookTabChanged>>',lambda e:self.sync(),add='+')
        self.show_group('Home');self.sync()

    def choose(self,name):
        self.sync()
        self.show_group(name)
        if name in self.primary:self.primary[name]()
        self.sync()

    def show_group(self,name):
        self.group=name
        for button in self.destination_buttons:button.destroy()
        self.destination_buttons=[]
        for index,(title,command) in enumerate(self.groups[name]):
            button=self.tracker.app.text_button(self.destinations,title,command)
            button.grid(row=index//4,column=index%4,sticky='ew',padx=5,pady=3)
            self.destinations.columnconfigure(index%4,weight=1)
            self.destination_buttons.append(button)

    def sync(self):
        page=self.tabs.select();title=self.locations.get(page,'Workspace');self.location.set(title)
        # A page opened by a tray/website shortcut exposes its own nearby actions.
        changed=page!=self.last_page;self.last_page=page
        if changed and title in self.primary and title!=self.group:self.show_group(title)
        elif changed and title not in self.primary:
            owner='Planning' if title in ('CP Info','Imperial') else 'Readers' if title in ('Live recognized items','Loot OCR reader') else 'History'
            if self.group!=owner:self.show_group(owner)
        c=self.tracker.app.colors
        for name,button in self.buttons.items():button.configure(bg=c['violet'] if name==self.group else c['panel2'])
