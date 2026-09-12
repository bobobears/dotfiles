# Driving a live Firefox via X11 (python-xlib + XTest, no sudo)

Use when browser_exec/CDP cannot attach to the user's session (e.g. Firefox on xrdp display :10). No root needed; install into a throwaway venv: `uv pip install python-xlib pillow lz4`.

## Validated pieces
- **Find the main window by WM_CLASS, not title.** `_NET_WM_NAME` is UTF8_STRING and python-xlib's get_wm_name() reads it unreliably. Walk the root tree (`w.query_tree().children`, recursive), collect windows whose WM_CLASS contains "firefox", pick the largest visible (w>400, h>300).
- **Force input focus** — required before any key will land:
  ```python
  D.set_input_focus(win, X.RevertToPointerRoot, X.CurrentTime)  # 3 args: focus, revert_to, time
  ```
  Then verify: `f = D.get_input_focus(); f.focus.id == win.id`.
- **Focus drift is the #1 failure mode.** Focus can sit on a 1x1 internal window; `_NET_ACTIVE_WINDOW` ClientMessage to root does NOT reliably work in xrdp sessions (no WM honoring it). Always set + verify focus immediately before sending keys.
- **XTest key events take KEYCODES — and Shift must be pressed explicitly.** A naive `keysym_to_keycode` + press/release types uppercase as lowercase (`'TEST123'`→`test123`), `_` as `-`, and symbols like `( ) { } + "` as their base-key equivalents or nothing at all. This silently corrupts every non-lowercase command — the #1 cause of "short string commands work, anything with symbols fails" (it masquerades as autocomplete/focus problems; a symbol-heavy canary proves it). Also: `XK.string_to_keysym(ch)` returns 0 for ASCII symbols on some python-xlib builds; X11 Latin-1 keysyms == `ord(ch)`, so use that directly:
  ```python
  from Xlib.ext import xtest
  _kmin = 8
  _keymap = D.get_keyboard_mapping(_kmin, 255 - _kmin + 1)   # list of per-keycode arrays; do NOT index [0]
  def resolve_key(ksym):
      base_kc = shift_kc = None
      for i, arr in enumerate(_keymap):
          a = list(arr)
          if len(a) >= 2:
              if a[0] == ksym and base_kc is None: base_kc = _kmin + i
              elif a[1] == ksym and shift_kc is None: shift_kc = _kmin + i
      if base_kc is not None: return (base_kc, False)
      if shift_kc is not None: return (shift_kc, True)
      return (D.keysym_to_keycode(ksym), False)   # fallback
  def key(D, ksym):
      kc, need_shift = resolve_key(ksym)
      if need_shift:
          xtest.fake_input(D, X.KeyPress, detail=D.keysym_to_keycode(XK.XK_Shift_L)); D.flush()
      xtest.fake_input(D, X.KeyPress, detail=kc); D.flush(); time.sleep(0.03)
      xtest.fake_input(D, X.KeyRelease, detail=kc); D.flush()
      if need_shift:
          xtest.fake_input(D, X.KeyRelease, detail=D.keysym_to_keycode(XK.XK_Shift_L)); D.flush()
  def type_text(D, text):
      for ch in text:
          o = ord(ch)
          ks = o if 32 <= o < 127 else (XK.string_to_keysym(ch) or o)
          key(D, ks)
      D.flush()
  ```
  Validate the channel with a symbol-heavy canary before real work: `document.title='SYM_'+(1+2)` must yield title `SYM_3`.
- **fake_input signature**: `fake_input(event_type, detail=0, time, root, x, y)` — for pointer events pass `root=<window id>`, `x=`, `y=` as keywords; button number goes in `detail` (1 = left).

## Navigation recipe (keys sent with verified focus)
```python
def combo(D, mod_ksym, main_ksym):  # e.g. Ctrl+L
    xtest.fake_input(D, X.KeyPress, detail=D.keysym_to_keycode(mod_ksym)); D.flush()
    time.sleep(0.05)
    key(D, main_ksym)
    xtest.fake_input(D, X.KeyRelease, detail=D.keysym_to_keycode(mod_ksym)); D.flush()

# after set_input_focus + verification:
combo(D, XK.XK_Control_L, XK.string_to_keysym("l"))   # focus address bar
time.sleep(0.3)
combo(D, XK.XK_Control_L, XK.string_to_keysym("a"))   # select existing text
# type_text(url): one key() per character
key(D, XK.string_to_keysym("Return"))
```

## Verify the load (do NOT rely on screenshots or titles alone)
1. Wait ≥10s.
2. Scan cache2 entries with mtime in the last ~3 min; decompress and check for the expected page content/URL (recipe: firefox-cache2-extraction.md §1).
3. Cross-check places history — mind the immutable/WAL caveat (§2 there).

## Web Console JS channel (in-page actions without new navigations)
Once typing works, execute arbitrary page JS via Firefox's Web Console — this is how you open internal tabs, read live DOM, and trigger AJAX on frame portals:
- Deterministic focus reset: `Escape` → `F12` → `Ctrl+Shift+K`. Ctrl+Shift+K is a TOGGLE; the 3-key sequence lands in "console focused" regardless of prior DevTools state.
- Clear the input before typing: `Ctrl+A` + `Delete`. Residual text from failed commands concatenates with new ones and produces silent syntax errors.
- Route results to `document.title`, read back with `xprop -id <win> _NET_WM_NAME | head -1` — no vision model needed. Keep typed payloads short; for bulk data use the local-relay pattern below.

## Long JS: inject via a local server, don't type it
Typing multi-hundred-char JS char-by-char is fragile and slow. Instead host the payload on 127.0.0.1 and type ONE short command:
```js
fetch('http://127.0.0.1:8897/p.js').then(r=>r.text()).then(eval)
```
- The serving side MUST send `Access-Control-Allow-Origin: *` — plain `python -m http.server` does NOT, and the response-reading GET then fails silently (fetch resolves, `.text()` rejects; nothing lands in your relay log). Subclass `SimpleHTTPRequestHandler.end_headers` to add the header.
- Nuance: a simple cross-origin POST with a text/plain body is a "simple request" — it works even without CORS on the receiver. Only response-reading (GET payloads, reading reply bodies) needs the header.
- Chinese in page JS: write the payload file as UTF-8 and use `\uXXXX` escapes for any string literals you must type inline; the fetched payload can contain raw CJK freely.

## In-page polling before extraction
After triggering a query/export via JS, don't extract immediately — poll inside the page:
```js
var tries=0;
function poll(){
  var m = doc.body.innerText.match(/总数据量\s*(\d+)\s*条/);   // site's own total-count text
  if((m && +m[1]>0) || ++tries>25){ extractAndPost(); return; }
  setTimeout(poll, 1500);
}
poll();
```
Adapt the regex to the portal's pager wording. This removes guesswork about AJAX load time.

## Frame portals (ASP.NET master-page sites)
Direct URL navigation to a subpage redirects back to the main frame — subpages must open inside the site's internal tab system. Find the tab-opening function in cached JS/HTML (e.g. ExtJS `addTab(Pages, 'title', '/pages/X.aspx', '')`), then call it from the Web Console channel above. Verify the load by cache-mtime scan for the aspx URL.

## Data return: local relay server
Run a tiny HTTP server on 127.0.0.1 (any port) and have page JS `fetch('http://127.0.0.1:<port>/x', {method:'POST', body: <table data>})`. Bypasses title-length limits and unavailable vision models; zero traffic to the remote host.

## Export-button download flow (full dataset, one request)
When the report page has an Excel/CSV export control:
1. Enumerate controls first (`querySelectorAll('input,button,a')` → id/type/value/text) to find the exact button — don't guess ids.
2. Stub `doc.defaultView.confirm = m => true` (and capture alerts) BEFORE `.click()`, or the confirm dialog blocks and nothing downloads.
3. Watch the browser's download dir: file appears with a `.part` suffix while in progress; poll until it disappears, then parse. ASP.NET "导出Excel" typically yields genuine OLE2 .xls → `pd.read_excel(f)` (xlrd). Header rows are often 1–2 rows of title/region text — inspect before setting `header=`.
4. Cross-check parsed row count against the page's total-count text; report both to the user.

## Pitfalls
- A window that looks like a save dialog may be another app entirely (observed: the Hermes desktop, 1220x800, no WM properties). Verify via `xwininfo -root -tree` parent chain before acting on it.
- Keep request rate human: one navigation per ≥10s; batch nothing. The whole point is not tripping the remote WAF/firewall.
- **fcitx/IME intercepts XTest keys**: ASCII gets converted to pinyin garbage (URL dots → `。`, letters → pinyin words). Stop it before any typing: `pkill -f fcitx` (exit -15 is fine — it matches its own command line; confirm with `pgrep -x fcitx`), restore after the job (`fcitx &`).
- **Session idle timeout (~20 min on ASP.NET portals)**: after the user re-logs in, execute the full plan immediately. Fix tooling problems BEFORE asking for a login — every expiry costs another manual captcha login (captcha images can't be read automatically).
- **`pkill -f <script>` kills your own shell** when the pattern matches the calling command line (exit -15 mid-cleanup). Kill temp servers by exact PID (`pgrep -af ... | grep -v pgrep`, then `kill <pid>`) or use a pattern that can't match the wrapper.
- **Don't navigate away from the platform page while debugging** — e.g. testing clipboard paste with `about:blank` in the address bar destroys the logged-in tab and forces another manual login. Test risky input paths on throwaway pages only when you don't need the current one.