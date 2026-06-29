---
name: native-mcp
description: "MCP client: connect servers, register tools (stdio/HTTP)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [MCP, Tools, Integrations]
    related_skills: [mcporter]
---

# Native MCP Client

Hermes Agent has a built-in MCP client that connects to MCP servers at startup, discovers their tools, and makes them available as first-class tools the agent can call directly. No bridge CLI needed.

## When to Use

- Connect to MCP servers and use their tools from within Hermes Agent
- Add external capabilities (filesystem access, GitHub, databases, APIs) via MCP
- Run local stdio-based MCP servers (npx, uvx, or any command)
- Connect to remote HTTP/StreamableHTTP MCP servers
- Have MCP tools auto-discovered and available in every conversation

## Prerequisites

- Hermes Agent with `hermes` CLI accessible
- MCP servers you want to connect to (local scripts or remote endpoints)

## Configuration

MCP servers are configured in `~/.hermes/config.yaml` under the `mcp_servers` key:

```yaml
mcp_servers:
  my-server:
    transport: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
```

Available transports:
- `stdio`: local command (npx, uvx, python, etc.)
- `http`: remote SSE endpoint

## Commands

```bash
# List configured MCP servers
hermes mcp list

# Enable a server
hermes mcp enable my-server

# Disable a server
hermes mcp disable my-server

# Re-scan and reload all enabled servers
hermes mcp reload

# Get tool list for a server
hermes mcp tools my-server

# Test a tool call
hermes mcp call my-server tool_name '{"arg": "value"}'

# View logs
hermes mcp logs my-server
```

## Verification

After configuration, check:
- `hermes mcp list` shows the server
- `hermes mcp enable my-server` works
- Tools appear in your available tools list
