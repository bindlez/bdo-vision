"""Review the actual native overlay using synthetic data; no profile, OCR or ledger."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from live_hud import LiveHUD
from drop_reveal import DropReveals

root=tk.Tk();root.withdraw()
app=SimpleNamespace(root=root,save_quietly=lambda:None)
tracker=SimpleNamespace(app=app,platform_preferences={'overlay':{'corner':'custom','position':[150,150],'seconds':14,'motion':False}})
grind=SimpleNamespace(tracker=tracker,pause=lambda:None)
live=SimpleNamespace(grind=grind,settings=lambda:None,window=None);grind.live=live;tracker.grind=grind
live.craft_panel=SimpleNamespace(toggle=lambda:None,retile=lambda:None,close=lambda:None)
live.hud=LiveHUD(live);live.window=live.hud.surface.window
live.hud.update({'available':True,'sessionActive':True,'status':'Yzrahid Highlands / SAMPLE',
                 'value':1452000000,'rate':678000000,'time':'00:42:18 / 00:02:40',
                 'silverGoal':2000000000,'latest':[{'quantity':1,'item':"Kabua's Artifact"}]})
big=SimpleNamespace(app=app,tracker=tracker,celebrate=tk.BooleanVar(value=True),toast=None,open=lambda:None)
big.reveals=DropReveals(big);tracker.big_drops=big
def preview():big.reveals.offer({'category':'Big Drop','item':"Kabua's Artifact",'quantity':1,'value':9350000000,'preview':True})
preview()
if '--framed' in sys.argv:
    # Regular review windows let accessibility tools inspect the real widgets.
    # This is test-only chrome; production always uses passive tool windows.
    import ctypes
    from game_overlay import native_handle
    for window in (live.window,big.toast):
        window.overrideredirect(False);window.update_idletasks()
        user32=ctypes.windll.user32;handle=native_handle(window)
        style=user32.GetWindowLongW(handle,-20)
        user32.SetWindowLongW(handle,-20,style & ~0x80)
    big.reveals.duration=55
# Short-lived inspection only; never leave a topmost mock running indefinitely.
root.after(60000,root.destroy)
root.mainloop()
