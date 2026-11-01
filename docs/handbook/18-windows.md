# 18 · Windows integration and lifecycle

## Window identity and visibility

`windows_bdo.py` owns Windows-specific discovery and verification. A title that looks like Black Desert is not sufficient proof; verify the expected executable identity and visible bounds. Tool capture requires the verified foreground game. Quest capture can use a visible background game only when the exact quest region passes occlusion checks. A minimized/tray game has no readable pixels.

The app must reacquire bounds when the game moves or loses focus. Test nonzero desktop origins and client sizes, not just a maximized game at `(0,0)`. DPI and UI scale affect geometry and font sizes. Anchor-based heuristics should be expressed in client coordinates with documented scaling, then validated at multiple resolutions.

## Input and tray controls

Vision observes the game; it does not automatically play it. Tray/restoration and explicit user-triggered shortcuts are isolated behind verified window checks. Never attach a game input action to an OCR value change. Windows can reject focus changes while a user is typing; handle that as an unavailable operation, not a reason to send keys blindly to whichever app is foreground.

Native tray restoration is best-effort and should remain user-initiated. Test that the intended game was restored, not just that an API call returned. Keep errors actionable and preserve the app's own taskbar/window restoration route. Automated tests cover contracts, but shell/tray behavior also needs a real Windows check.

## Single instance

`InstanceLock` uses an OS-released lock on a profile file. It avoids stale PID cleanup deleting state. A second launch uses runtime status and `/health` to request restoration of the existing app. It can therefore appear that a new release did not start when the old instance was still active. Do not bypass the lock to run two writers against the same profile.

Development uses a separate profile and thus a separate lock. It may also need a different available bridge port. Always pair the browser with the instance you intended to test. A shared hard-coded port is not a substitute for checking instance and history identities.

## Shutdown and installation

Stop scheduled callbacks, mark controllers closed, close feature viewers, close the bridge and ledger, then destroy Tk. Workers must not publish stale results after generation changes. Do not block the UI waiting indefinitely for OCR. A normal app close lets the process release its lock; an installer should refuse to replace a running copy rather than kill it.

The handbook and developer tools have no game-loop presence. Opening the documentation in a browser has its own browser memory cost, but it adds no polling, model or graph runtime to the Windows tracker.
