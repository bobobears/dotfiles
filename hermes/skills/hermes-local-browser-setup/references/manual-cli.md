# Manual agent-browser CLI diagnostics

Test the browser backend directly, outside Hermes, to isolate whether a failure is in Hermes's wrapper or in agent-browser itself.

## Finding the binary
It lives in the npx cache (Hermes resolves it lazily via `npx agent-browser`):
```bash
ls ~/.npm/_npx/*/node_modules/agent-browser/bin/agent-browser-linux-arm64
```
Assign to a variable, e.g. `AB=$(ls ~/.npm/_npx/*/node_modules/agent-browser/bin/agent-browser-linux-arm64 | head -1)`.

## Commands
- Launch test: `$AB open http://example.com` — success prints "✓ Example Domain" plus the URL.
- Kill stale daemon: `$AB close` (required before any flag/config change takes effect).
- Verbose launch logs: add `--debug`.
- One-off overrides: `--executable-path <chrome>` and `--args "--no-sandbox"` — but these are ignored while a daemon is already running; `close` first.
- Attach to an existing browser instead of launching: `--cdp <port>`.

## Reading failures
- "Chrome not found. Checked: ..." → no discoverable binary; fix via `~/.agent-browser/config.json` (see SKILL.md), not by retrying install on ARM64.
- "No usable sandbox!" in Chrome stderr → missing `--no-sandbox`.
- "daemon already running" warnings → stale daemon holding old flags; `$AB close`, then relaunch.
