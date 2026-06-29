---
name: debugging-hermes-tui-commands
description: "Debug Hermes TUI slash commands: Python, gateway, Ink UI."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, hermes-agent, tui, slash-commands, typescript, python]
    related_skills: [python-debugpy, node-inspect-debugger, systematic-debugging]
---

# Debugging Hermes TUI Slash Commands

## Overview

Hermes slash commands span three layers — Python command registry, tui_gateway JSON-RPC bridge, and the Ink/TypeScript frontend.

## Debugging Approach

### Layer 1: Python Command Registry

Commands are registered in `hermes/cli/commands.py` (or similar). Check:

```bash
# List registered commands
hermes help

# Check command source
grep -r "def.*<command>" ~/.hermes/ --include="*.py"
```

Common issues:
- Command not imported in the registry
- Decorator missing (`@app.command()`)
- Function signature wrong

### Layer 2: tui_gateway JSON-RPC Bridge

The gateway sends commands as JSON-RPC requests. Check gateway logs:

```bash
# View gateway logs
hermes gateway logs

# Check if command is being received
grep -i "<command>" ~/.hermes/logs/gateway*.log
```

Common issues:
- Gateway not running or crashed
- Command payload format mismatch
- Permission/authentication issues

### Layer 3: Ink/TypeScript Frontend

The TUI frontend uses Ink + React/TypeScript. Debug with:

```bash
# Open Chrome DevTools for the TUI
# Hermes Desktop: View → Toggle Developer Tools

# Check console for errors
# Look for React component errors and state issues
```

Common issues:
- Component not rendering
- State not updating after command execution
- Event handler not connected

## Common Fixes

1. **Command missing from autocomplete**: Check Python registry → Restart TUI
2. **Command runs but UI doesn't update**: Check gateway → Restart gateway
3. **Command not found in TUI but works in CLI**: Check Ink component registration
