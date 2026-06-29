# Driving Interactive Terminal Wizards from Hermes

`hermes gateway setup` uses a terminal UI that **does not work** in plain pipe/foreground mode. This pattern applies to any Hermes interactive setup wizard.

## The Pattern

```python
# Step 1: Start in background+PTY
terminal(command="hermes gateway setup", background=true, pty=true, notify_on_complete=true)

# Step 2: Read output to see current prompt
process(action="log", session_id="proc_xxx")

# Step 3: Send inputs via submit (which sends text + Enter)
process(action="submit", data="3", session_id="proc_xxx")   # select option
process(action="submit", data="Y", session_id="proc_xxx")   # confirm
```

## Rules

1. **Always use `background=true` + `pty=true`** — foreground dies with exit code 1
2. **Use `process(action="submit")`** to send text followed by Enter
3. **Poll/log between submits** to confirm what prompt the wizard is showing
4. **Use `notify_on_complete=true`** on the initial terminal call so the system alerts you when the wizard finishes

## Why This Works

`pty=true` allocates a pseudo-terminal, which the interactive curses/terminal-UI library expects. `background=true` keeps the process alive so you can interact with it step by step. `process(action='submit')` sends the text + carriage return, which is how terminal-UI programs read input (vs `write` which sends raw text without Enter).
