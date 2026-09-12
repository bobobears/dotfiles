---
name: web-session-extraction
description: Extract data from a logged-in web app, zero extra requests.
---

# Web Session Extraction (zero / minimal request)

Extract data from a web platform the user has already logged into — typically a sensitive internal/government system where extra traffic could trip its firewall/WAF or violate policy. Two-phase approach: **mine local browser state first (zero requests)**, then drive the live browser only for what is missing (one request per page, human-paced).

## When to use
- User says "I'm logged in at <url>, can you extract data?" plus a constraint like "don't trigger their firewall"
- Target is an authenticated ASP.NET/PHP portal with report pages; re-login would be noisy or impossible (no credentials)
- browser_exec / CDP tools cannot attach to the user's existing session (e.g. Firefox on xrdp display :10)

## Phase 0 — Locate the live session
1. Find which browser/profile holds it: `ls ~/.config/mozilla/firefox/`, running processes, X displays (`/tmp/.X11-unix/`).
2. Confirm what is loaded WITHOUT network: decode `sessionstore-backups/recovery.jsonlz4` (private mozLz40 format) and/or query places history.
3. Check cookies for the target host — if absent while history shows a logged-in main page, the session is memory-only; **never close that browser window**.

## Phase 1 — Zero-request extraction (always do this first)
Firefox's disk cache already holds every loaded page. Mine it:
- Entries live in `~/.cache/mozilla/firefox/<profile>/cache2/entries/*` (flat binary files, no on-disk index).
- Each entry = header region (request URL as plain text) + gzip payload starting at `\x1f\x8b`. Scan for the magic bytes and decompress with `zlib.decompressobj(16+MAX_WBITS)`.
- From cached HTML you get: full menu structure, all page URLs (frames/links), AJAX handler endpoints — often enough to plan the entire extraction before sending a single request.

Recipes + code: `references/firefox-cache2-extraction.md`

## Phase 2 — Minimal-request navigation (only for data not in cache)
Drive the user's live Firefox via X11 (python-xlib + XTest, no sudo needed):
- One page per request; wait ≥10s between navigations (human pace). Batch nothing.
- Verify each load by scanning cache entries by mtime — NOT screenshots (vision may be unavailable/slow) and NOT window titles alone.
- Extract the new page from cache immediately after it lands.
- **Prefer the site's own export control.** Report pages on this class of portal usually have an Excel/CSV export button (often behind a confirm dialog). One click downloads the FULL dataset locally — far less traffic than paginating N pages. Trigger it via in-page JS (`btn.click()` after stubbing `confirm` to return true), then verify by watching the `.part` suffix disappear on the file in the browser's download dir, and parse (genuine OLE2 .xls → pandas+xlrd; cross-check row count against the page's 总数据量).
- **Typing must be Shift-aware** (keyboard-mapping lookup; see reference §XTest) — naive keysym→keycode typing silently corrupts uppercase/symbols and makes every non-trivial command fail.
- Prefer the **Web Console JS channel** for in-page actions (open internal tabs, read live DOM); frame portals reject direct subpage URLs. Bulk data returns via a 127.0.0.1 relay server, not window titles.

Recipe + pitfalls: `references/x11-firefox-navigation.md`

## Pitfalls
- `sqlite3 file:...?immutable=1` reads a stale snapshot: uncheckpointed WAL contents are invisible, so brand-new history visits may not appear. Fine for quick checks; use the online-backup API (or copy DB + -wal) when fresh state matters — backup can block while Firefox holds locks, run it with a timeout.
- cache2 entries that scan as "0B payload" = URL only in header or non-gzip content; don't conclude the page is missing.
- Big JS bundles (e.g. ECharts ~1MB) false-positive on keyword greps — classify by decompressed content (`<!DOCTYPE`/`<html` vs `{`/`[` JSON).
- A window that looks like a save dialog may be another app entirely (this class of session: it was the Hermes desktop). Verify identity via `xwininfo -root -tree` parent chain before acting on it.
- ASP.NET portals: report pages often load numbers via AJAX handlers — static HTML has labels but no values. Find the .ashx endpoints in cached JS/HTML first, then budget one request per report page.
