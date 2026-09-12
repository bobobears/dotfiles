#!/usr/bin/env python3
"""Drive Firefox on DISPLAY :10 via XTest. Usage: xtype.py <canary|fetch:<file>|console_only>
Run with: uv run --with python-xlib python3 xtype.py <cmd> (DISPLAY=:10)
Payload files are served by relay.py at http://127.0.0.1:8899/<file>.
"""
import sys, time
from Xlib import X, XK, display
from Xlib.ext import xtest

D = display.Display()
root = D.screen().root

win = None; best = 0
def rec(w):
    global win, best
    try:
        cls = w.get_wm_class()
    except Exception:
        cls = None
    if cls and any('firefox' in (c or '').lower() for c in cls):
        g = w.get_geometry()
        if g.width > 400 and g.height > 300 and g.width * g.height > best:
            best = g.width * g.height; win = w
    try:
        for c in w.query_tree().children:
            rec(c)
    except Exception:
        pass

rec(root)
assert win is not None, 'no firefox window found'
print('window:', hex(win.id))

D.set_input_focus(win.id, X.RevertToPointerRoot, X.CurrentTime)
D.flush()
time.sleep(0.3)
f = D.get_input_focus().focus
if f.id != win.id:
    print('WARN: focus is', hex(f.id), 'not main window')

_kmin = 8
_keymap = D.get_keyboard_mapping(_kmin, 256 - _kmin)

def resolve_key(ksym):
    base_kc = shift_kc = None
    for i, arr in enumerate(_keymap):
        a = list(arr)
        if len(a) >= 2:
            if a[0] == ksym and base_kc is None:
                base_kc = _kmin + i
            elif a[1] == ksym and shift_kc is None:
                shift_kc = _kmin + i
    if base_kc is not None: return (base_kc, False)
    if shift_kc is not None: return (shift_kc, True)
    return (D.keysym_to_keycode(ksym), False)

def key(ksym):
    kc, need_shift = resolve_key(ksym)
    if need_shift:
        xtest.fake_input(D, X.KeyPress, detail=D.keysym_to_keycode(XK.XK_Shift_L)); D.flush()
    xtest.fake_input(D, X.KeyPress, detail=kc); D.flush(); time.sleep(0.03)
    xtest.fake_input(D, X.KeyRelease, detail=kc); D.flush()
    if need_shift:
        xtest.fake_input(D, X.KeyRelease, detail=D.keysym_to_keycode(XK.XK_Shift_L)); D.flush()

def type_text(text):
    for ch in text:
        o = ord(ch)
        ks = o if 32 <= o < 127 else (XK.string_to_keysym(ch) or o)
        key(ks)
    D.flush()

def combo(mod_ksym, main_ksym):
    xtest.fake_input(D, X.KeyPress, detail=D.keysym_to_keycode(mod_ksym)); D.flush()
    time.sleep(0.05)
    key(main_ksym)
    xtest.fake_input(D, X.KeyRelease, detail=D.keysym_to_keycode(mod_ksym)); D.flush()

def chord(ksyms):
    for k in ksyms[:-1]:
        xtest.fake_input(D, X.KeyPress, detail=D.keysym_to_keycode(k)); D.flush()
        time.sleep(0.05)
    key(ksyms[-1])
    for k in reversed(ksyms[:-1]):
        xtest.fake_input(D, X.KeyRelease, detail=D.keysym_to_keycode(k)); D.flush()

def focus_console():
    # deterministic: Escape -> F12 -> Ctrl+Shift+K (toggle lands console-focused)
    key(XK.string_to_keysym('Escape')); time.sleep(0.5)
    key(XK.XK_F12); time.sleep(1.2)
    chord([XK.XK_Control_L, XK.XK_Shift_L, XK.string_to_keysym('k')])
    time.sleep(0.8)

def clear_input():
    combo(XK.XK_Control_L, XK.string_to_keysym('a')); time.sleep(0.2)
    key(XK.string_to_keysym('BackSpace')); time.sleep(0.3)

def get_title(w):
    atom = D.intern_atom('_NET_WM_NAME')
    p = w.get_full_property(atom, X.AnyPropertyType)
    if not p: return None
    data = bytes(p.value).decode('utf-8', 'ignore').rstrip('\x00')
    return data

cmd = sys.argv[1] if len(sys.argv) > 1 else 'canary'

if cmd == 'canary':
    focus_console()
    clear_input()
    type_text("document.title='SYM_'+(1+2)")
    key(XK.string_to_keysym('Return'))
    time.sleep(2.0)
    print('TITLE:', get_title(win))
elif cmd.startswith('fetch:'):
    fname = cmd.split(':', 1)[1]
    focus_console()
    clear_input()
    type_text("fetch('http://127.0.0.1:8899/%s').then(r=>r.text()).then(eval)" % fname)
    key(XK.string_to_keysym('Return'))
    print('payload sent:', fname)
elif cmd == 'console_only':
    focus_console()
    clear_input()
    print('console focused, input cleared')
