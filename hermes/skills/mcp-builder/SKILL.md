---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools.
license: MIT
---

# MCP Server Development Guide

## Overview

Create MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools.

## Process

### Phase 1: Deep Research and Planning

1. Understand the target API thoroughly (read docs, test endpoints)
2. Design tool naming: use consistent prefixes (e.g., `github_create_issue`, `github_list_repos`)
3. Balance comprehensive API coverage with specialized workflow tools

### Phase 2: Implementation

Choose a framework:
- **Python**: `fastmcp` (preferred) or `mcp` library
- **TypeScript**: `@modelcontextprotocol/sdk`

Implementation checklist:
- [ ] Define clear tool schemas with proper descriptions
- [ ] Handle errors gracefully with descriptive messages
- [ ] Add logging for debugging
- [ ] Test each tool manually
- [ ] Add a `list_tools` endpoint that returns tool metadata

### Phase 3: Integration

- [ ] Add server to `~/.hermes/config.yaml` under `mcp_servers`
- [ ] Enable with `hermes mcp enable <server>`
- [ ] Verify tools appear with `hermes mcp tools <server>`
- [ ] Test each tool end-to-end

## Best Practices

- **Tool descriptions**: Write descriptions that help LLMs understand when to use each tool
- **Error handling**: Return user-friendly error messages, not raw stack traces
- **Input validation**: Validate inputs at the MCP server level
- **Resource cleanup**: Handle connection cleanup properly
- **Security**: Never expose sensitive credentials in tool responses

## Tools

The MCP server should expose tools that:
1. Cover the main CRUD operations of the target API
2. Include search/list operations with filtering
3. Handle pagination transparently
4. Return structured data (prefer JSON over raw text)
