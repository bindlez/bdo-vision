"""Verify a packaged build without captures, game input or a persistent server."""
import json,sys,tkinter as tk
from pathlib import Path
from version import APP_VERSION

def run_self_check(app_class,root_path,data_path):
    report={'version':APP_VERSION,'ok':False,'checks':{}}
    root=None;app=None
    try:
        import pywinauto
        report['checks']['tray_dependency']=bool(pywinauto)
        for name,path in {'planner':root_path.parent/'bdo-market-intelligence.html',
                          'fairycodex':root_path.parent/'fairycodex.html',
                          'recipes':Path(__file__).parent/'assets/recipes.json',
                          'item_names':Path(__file__).parent/'assets/item-names.json',
                          'cp_data':Path(__file__).parent/'assets/cp-data.json',
                          'structured_helper':root_path/'assets/vision-windows-ocr.exe',
                          'icon':root_path/'assets/bdo-lite.png'}.items():
            report['checks'][name]=path.is_file()
        root=tk.Tk();root.withdraw();app=app_class(root);root.update_idletasks()
        report['checks']['native_widgets']=bool(root.winfo_exists())
        from tkinter import ttk
        cp_tabs=ttk.Notebook(root);app.loot.cp_info.build(cp_tabs);root.update_idletasks()
        report['checks']['cp_native_widgets']=bool(app.loot.cp_info.frame.winfo_exists())
        report['checks']['cp_target_widgets']=app.loot.cp_info.target_view.tree.exists('owned')
        app.loot.cp_info.workerman.toggle()
        report['checks']['workerman_native_widgets']=bool(app.loot.cp_info.workerman.frame.winfo_exists())
        app.loot.cp_info.workerman.toggle()
        app.loot.imperial.build(cp_tabs);app.loot.imperial.recalculate(save=False)
        report['checks']['imperial_native_widgets']=bool(app.loot.imperial.frame.winfo_exists())
        from live_grind import stream_page
        report['checks']['stream_overlay_asset']=b'/stream-state' in stream_page()
        from workspace_nav import WorkspaceNavigation
        report['checks']['workspace_navigation_module']=callable(WorkspaceNavigation)
        report['checks']['cp_example']=app.loot.cp_info.report['routes'][1]['cp']==567
        report['checks']['history_integrity']=app.loot.ledger.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        report['checks']['bridge']=bool(app.bridge and app.bridge.server)
        if '--ocr-fixture' in sys.argv:
            import shutil
            from PIL import Image
            from loot_capture import recognize_feed
            fixture=Path(sys.argv[sys.argv.index('--ocr-fixture')+1])
            tess=shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            with Image.open(fixture) as image:
                result=recognize_feed(image,tess,'normal',True,data_path/'self-check-ocr')
            report['checks']['packaged_ocr']=any(e.item=='Elixir of Demihuman Hunt' and e.quantity==4 for e in result['events'])
        report['ok']=all(report['checks'].values())
    except Exception as exc:report['error']=str(exc)
    finally:
        if app:app.close()
        elif root:root.destroy()
    if '--self-check-report' in sys.argv:
        path=Path(sys.argv[sys.argv.index('--self-check-report')+1]);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    if sys.stdout:print(json.dumps(report))
    if not report['ok']:raise SystemExit(1)
