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
                          'icon':root_path/'assets/bdo-lite.png'}.items():
            report['checks'][name]=path.is_file()
        root=tk.Tk();root.withdraw();app=app_class(root);root.update_idletasks()
        report['checks']['native_widgets']=bool(root.winfo_exists())
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
