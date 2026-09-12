---
name: hermes-local-browser-setup
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
description: "Use when browser_exec fails to launch Chrome on ARM64."
metadata:
  hermes:
    tags: [browser, agent-browser, chromium, arm64, troubleshooting]
---

# Hermes Local Browser Setup (ARM64 host)

## When to use
- `browser_exec` / `browser_*` tools fail with "Chrome not found. Checked: agent-browser cache..." or a launch error.
- First-time setup of local browser automation on this machine.

## Host facts (why the default path fails)
- This host is Linux ARM64 (DGX Spark). Chrome for Testing ships **no Linux ARM64 build**, so `agent-browser install` always ends with "Chrome for Testing does not provide Linux ARM64 builds". Do not retry it — go straight to the config fix.
- A working Chromium already exists: Playwright's, at `~/.cache/ms-playwright/chromium-<rev>/chrome-linux/chrome`. List the dir to get the current revision; use the full `chrome` binary (not `chromium_headless_shell`).

## Fix procedure
1. Locate the binary: `ls ~/.cache/ms-playwright/` → pick `chromium-*/chrome-linux/chrome`; sanity-check with `<bin> --version`.
2. Write `~/.agent-browser/config.json`:
   ```json
   { "executablePath": "/home/bobobears/.cache/ms-playwright/chromium-<rev>/chrome-linux/chrome", "args": "--no-sandbox" }
   ```
   - `args` must be a **string**, not an array — the array form is rejected with "invalid type: sequence, expected a string".
3. Kill any running agent-browser daemon before relying on new config (`agent-browser close`, or run `close` via the npx-cache binary — see references/manual-cli.md). While a daemon lives, CLI flags are ignored ("--executable-path ignored: daemon already running"); config.json only applies to fresh daemons.
4. Verify with a minimal `browser_exec` call (`new_tab('http://example.com')` + `js('document.title')`) before doing real work — do not assume the fix landed because the file was written.

## Pitfalls
- Do NOT symlink chrome into `~/.agent-browser/browsers/`: a bare binary at that cache root is not discovered by the CLI's search. Use `executablePath` in config.json instead.
- `--no-sandbox` is mandatory on this host: without it Chrome FATALs with "No usable sandbox" (AppArmor user-namespace restriction).
- When driving Playwright directly from Python, pass `executable_path=` explicitly — the hermes venv's playwright may be pinned to a different build revision than what is installed, and default launch fails with "Executable doesn't exist at .../chromium_headless_shell-<other-rev>/...".

## Manual CLI diagnostics
Bypass Hermes to isolate whether a failure is in Hermes or in agent-browser itself: see `references/manual-cli.md`.
