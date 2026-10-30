# Review cycles

This review log is a reproducible engineering checklist, **not** a claim of an independent AI agent review.

## Pass 1: Functional safety
- Legacy `/durability` contract retained.
- `/ack` requires matching instance ID and known signal.
- Ctrl+V sent only after a two-second delay and verified BDO foreground.
- Windows tray restore remains best-effort, not guaranteed.

## Pass 2: OCR correctness
- Added regression coverage for 1350 vs (350.
- Legitimate 1350 never rewritten without expected-timer evidence.
- Readings with maximum < current discarded.

## Pass 3: UX and lifecycle
- Renamed the desktop folder for a clean project layout.
- Removed manual Start / Re-sync naming from the primary OCR flow.
- Large tool changes now require corroboration before the timer resets.

## Pass 4: Release readiness
- Added CI tests and Windows executable build artifact.
- Added dependency boundaries and `.gitignore`.
- Confirmed Python/JavaScript syntax and bridge integration tests locally.

## Remaining external review
A separate AI agent has not reviewed this project in this session: no agent-delegation capability was available.
Recommended review focus: Tkinter thread safety, Windows tray icon reliability, OCR performance, and PNA browser policy.

## V9 optimization and regression review

- **Speed:** Reviewed the OCR subprocess loop and replaced 18 mandatory passes with a maximum of six and optional early exit after agreement.
- **Accuracy:** Retained prior-reading validation and added a passive pace estimator instead of automatically changing craft speed based on noisy OCR.
- **Data integrity:** New `should_publish` policy avoids resetting the browser timer for identical readings while always transmitting tool session changes.
- **Timer accuracy:** Desktop estimator now uses a monotonic elapsed clock from capture through processing; the browser still anchors to the screenshot's epoch timestamp.
- **End-to-end:** Browser smoke test verifies browser acknowledgment, in-place updates and tool replacement.
- **Not tested:** Actual GPU performance, BDO in-game screenshot accuracy and native Windows tray integration require device testing. No independent AI-agent review was performed.
