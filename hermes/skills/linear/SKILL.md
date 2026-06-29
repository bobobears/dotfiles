---
name: linear
description: "Linear: manage issues, projects, teams via GraphQL + curl."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [LINEAR_API_KEY]
  commands: [curl]
metadata:
  hermes:
    tags: [Linear, Project Management, Issues, GraphQL, API, Productivity]
---

# Linear — Issue & Project Management

Manage Linear issues, projects, and teams directly via the GraphQL API using `curl`. No MCP server, no OAuth flow, no extra dependencies.

## Setup

1. Get a Linear API key from https://linear.app/settings/api
2. Set the environment variable:
   ```bash
   export LINEAR_API_KEY="lin_api_xxxxxxxxxxxx"
   ```

## Common Operations

### List Teams
```bash
curl -s https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query": "{ teams { nodes { id name key } } }"}'
```

### Create Issue
```bash
curl -s https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id identifier title } } }",
    "variables": {
      "input": {
        "title": "Fix login bug",
        "description": "Users cannot login with SSO",
        "teamId": "<team-id>"
      }
    }
  }'
```

### List Issues
```bash
curl -s https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query": "{ issues { nodes { id identifier title state { name } } } }"}'
```

### Update Issue State
```bash
curl -s https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation($input: IssueUpdateInput!, $id: String!) { issueUpdate(input: $input, id: $id) { success } }",
    "variables": {
      "id": "<issue-id>",
      "input": { "stateId": "<state-id>" }
    }
  }'
```
