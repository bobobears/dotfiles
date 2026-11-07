# Firefox crash on xrdp: profile corruption and relaunch

When the live Firefox instance (the one holding the only session) dies or its profile corrupts, relaunching is the hard part. Validated on this machine's xrdp :10 / Ubuntu Firefox.

## Diagnose the death
- `pgrep -af firefox` — is it actually gone, or just windowless?
- Crash cause: `~/.xsession-errors`, `journalctl --user`, `dmesg | tail` (OOM/segfault). Often nothing is logged — a hard crash leaves no trace.
- Profile state: `places.sqlite` 0 bytes / `recovery.jsonlz4` undecodable / `urlHistory.json` empty = profile hard-crashed. `recovery.jsonlz4` is mozLz40 — decode with `lz4.block.decompress(raw, uncompressed_size=header)`, but after a hard crash it's usually empty anyway. If history is wiped, accept it — the session is in memory (see SKILL.md Phase 0), not on disk.

## Relaunch
- Normal launch (`firefox <url>` or `-new-instance`) may exit immediately on a corrupt/locked profile — process starts, no window ever appears, process vanishes. Don't loop on it.
- **`firefox -safe-mode <url>` is the reliable fallback.** Expect a "Open Firefox in Troubleshoot Mode?" dialog — dismiss with XTest: find the dialog window (`xwininfo -root -tree`), focus it, press Return (or Escape). The main window (WM_CLASS Navigator, ~1280x1040) appears afterward.
- Safe Mode disables extensions — fine for basic navigation and the relay/JS channel; the target portals here are plain ASP.NET.
- After any relaunch the **session is gone** (in-memory only, never persists to disk) — the user must re-login manually (captcha). Plan for it: fix all tooling issues BEFORE asking for the login.

## Focus/type channel quirks on this stack
- EWMH `_NET_ACTIVE_WINDOW` ClientMessage is unreliable in xrdp; the proven sequence is `w.map()` + `D.set_input_focus(win, X.RevertToPointerRoot, X.CurrentTime)` + click at window center. (`xconst` import errors from `Xlib.protocol` are cosmetic — fall back to `Xlib.X`.)
- **`BadRRModeError` from `display.flush()` during heavy XTest sequences** (rapid key events, resolution changes): it crashes the script mid-typing, leaving half-typed input in the field. Wrap the event loop in try/except around flush, and treat a flush error as "stop, re-focus, clear the field (Ctrl+A+Delete), retry" — never as "the type succeeded".
- Screenshots: `xwd -root` times out on 2560x1440 xrdp; use python-xlib `root.get_image()` → PIL instead (see x11-window-recovery skill's screenshot note).
