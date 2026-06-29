---
name: github-agent-skill-search
description: Workflow to search GitHub for agent skill repositories, sorted by stars.
---

# GitHub Agent Skill Search

Search GitHub for "agent skill" repositories, sorted by stars, returning the top 10.

## Prerequisites

- `curl` and `python3` (for JSON formatting) — both available on the system
- **Optional but recommended**: `gh` CLI authenticated → raises API rate limit from 60 to 5000 req/h

## Usage

### Basic Search (no auth needed)

```bash
# Search for agent skill repos — unauthenticated, 60 req/h limit
curl -s "https://api.github.com/search/repositories?q=agent+skill&sort=stars&order=desc&per_page=10" | python3 -m json.tool
```

### With Authentication (5000 req/h)

```bash
# If gh is installed and authenticated
gh search repos "agent skill" --sort stars --limit 10 --json name,owner,stargazersCount,description,url

# Fallback: curl with token
GITHUB_TOKEN="$(gh auth token 2>/dev/null)"
[ -n "$GITHUB_TOKEN" ] || GITHUB_TOKEN="$(grep 'github.com' ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')"
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/search/repositories?q=agent+skill&sort=stars&order=desc&per_page=10"
```

Or use the browser: `https://github.com/search?q=agent+skill&type=repositories&s=stars&o=desc`

## Output Format

Return a formatted table with:
- Repository name
- Star count
- Brief description
- URL

Useful for discovering:
- New MCP servers
- Hermes or Claude Code skills
- Agent frameworks and tools
- Prompt engineering resources

## Pitfalls

1. **Rate limiting**: Unauthenticated GitHub API calls are capped at **60 requests/hour**. If you hit `{"message": "API rate limit exceeded"}`, use the authenticated path above (gh or token).
2. **China network**: `api.github.com` is accessible from mainland China but can be slow. Do NOT route API calls through `ghproxy.net` — the proxy is for raw URLs and git clone, not API endpoints. Use SSH or direct HTTPS for API.
3. **Unstable results**: Search results can vary by authentication level. Authenticated searches return richer results and are less likely to be truncated.
4. **jq may not be installed**: Use `python3 -m json.tool` as a reliable fallback — it's available wherever Python 3 is installed.
