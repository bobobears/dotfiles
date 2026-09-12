---
name: install-community-skill
description: >
  Install community Hermes skills from GitHub — download SKILL.md + support files,
  run security audit, place in ~/.hermes/skills/ with proper structure.
  Covers: gh API download when git clone fails, safety scanning, reference file extraction.
---

# Install a Community Skill from GitHub

Use this when the user asks to install a Hermes skill from a GitHub repo
(e.g., from the skill ranking, a recommendation, or a direct link).

## Prerequisites

- Target repo has a `SKILL.md` somewhere in the tree (root, `skills/<name>/`, or similar)
- `gh` CLI authenticated (`gh auth status`) — **but unauthenticated `curl` to GitHub REST API also works** for public repos (60 req/hr rate limit is sufficient for skill installs)

## Workflow

### 1. Identify the skill and locate SKILL.md

Get the repo owner/name (e.g., `eugeniughelbur/obsidian-second-brain`).

**SKILL.md is NOT always at the root.** Many repos (especially skill collections like superpowers-zh) place skills under `skills/<skill-name>/SKILL.md`. Check both locations:

```bash
# Check root first
curl -sL --max-time 10 -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>/contents/SKILL.md" -o /tmp/check.json
python3 -c "import json; d=json.load(open('/tmp/check.json')); print(d.get('name','NOT FOUND'))"

# If not at root, check the tree for skills/ subdirectory
curl -sL --max-time 10 -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1" -o /tmp/tree.json
python3 -c "import json; d=json.load(open('/tmp/tree.json')); [print(i['path']) for i in d.get('tree',[]) if 'SKILL.md' in i['path']]"
```

**Determine the default branch** — it's not always `main`:
```bash
curl -sL --max-time 10 -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>" -o /tmp/repo.json
python3 -c "import json; print(json.load(open('/tmp/repo.json')).get('default_branch','main'))"
```

If the repo has no SKILL.md anywhere — not a valid skill, skip.

### 2. Download SKILL.md

**Preferred: GitHub REST API via `curl` (works without `gh` auth, reliable from China):**

```bash
curl -sL --max-time 20 -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>/contents/<path-to-SKILL.md>?ref=<branch>" \
  -o /tmp/<skill-name>/raw.json
# Decode the base64-encoded content
python3 -c "
import json, base64
with open('/tmp/<skill-name>/raw.json') as f: data = json.load(f)
content = base64.b64decode(data['content']).decode('utf-8')
with open('/tmp/<skill-name>/SKILL.md','w') as f: f.write(content)
print(f'OK: {len(content)} chars')
"
```

**Fallback: `gh api` (requires auth, higher rate limit):**
```bash
gh api repos/<owner>/<repo>/contents/<path-to-SKILL.md> --jq '.content' | base64 -d > /tmp/<skill-name>/SKILL.md
```

**Fallback: git clone (if network allows):**
```bash
git clone --depth 1 https://github.com/<owner>/<repo>.git /tmp/<skill-name>/
```

**Do NOT use `curl | bash` or `wget` from unknown sources.**

### 2b. Batch install (skill collections)

Some repos (e.g., superpowers-zh) contain multiple skills under `skills/<name>/`. When installing several at once:

1. List all SKILL.md paths in the repo tree
2. Compare against existing local skills (`ls ~/.hermes/skills/`) to find which are missing
3. Download only the missing ones in a loop
4. Run security audit on the batch before installing any

### 2c. Repairing a half-installed skill (tap-based)

Some skills arrive as **SKILL.md only**, with the support files never
downloaded, so the documented commands fail with `No such file or directory:
scripts/...`. The install source is recorded in the taps file:

```bash
python3 -c "import json;print(json.dumps(json.load(open('$HOME/.hermes/skills/.hub/taps.json')),indent=2))"
```

That lists `{repo, path}` pairs. **Do not** rely on
`hermes skills inspect/install <name>` to repair it — it blocks on a direct
GitHub fetch and hangs (timed out at 180s here). Pull the whole repo over the
REST API instead (works from China, ~0.3s), then verify against the repo's own
`SHA256SUMS.txt` before installing:

```bash
curl -sL --max-time 20 -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1" -o /tmp/tree.json
# then download every blob in tree.json via the contents API (base64), preserving paths
sha256sum -c SHA256SUMS.txt      # in the staging dir, before copying anything into skills/
```

Pin `<branch>` from `GET /repos/<owner>/<repo>` instead of assuming `main`.
Also diff the repo SKILL.md against the local one — a half-installed skill is
often a stale version too (here 2.1.0 → 3.1.1), so repairing is also the
moment to upgrade.

### 2d. Generate runtime.conf when the skill asks for one

A skill whose SKILL.md says to read `Runtime`/`Command` from
`<skill_dir>/runtime.conf` expects that file to be created at install time —
it is gitignored and never shipped in the repo. Write it with an **absolute**
interpreter path so it does not depend on PATH:

```bash
printf 'Runtime: Python\nCommand: %s %s/scripts/<cli>.py\n' \
  /usr/bin/python3 "$HOME/.hermes/skills/<name>" > "$HOME/.hermes/skills/<name>/runtime.conf"
```

First confirm the interpreter actually imports the skill's dependencies
(`/usr/bin/python3 -c "import requests"`): the name `python3` resolves to a
venv in one shell and `/usr/bin/python3` in another, so a PATH-relative
command in `runtime.conf` becomes flaky.

### 3. Security audit

Before installing, scan the SKILL.md and any scripts for dangerous patterns:

```bash
grep -n 'subprocess\|os\.system\|eval \|exec \|rm -rf\|curl \|wget \|pip install\|apt install\|chmod 777\|sudo \|requests\.\|urllib\|base64 -d\|__import__\|compile(' \
  /tmp/<skill-name>/SKILL.md /tmp/<skill-name>/scripts/*.py /tmp/<skill-name>/*.sh 2>/dev/null
```

Flag for review:
- `subprocess.run` / `os.system` — external command execution (may be OK for CLI tools)
- `curl` / `wget` — network calls (check if they download code or just fetch data)
- `pip install` / `apt install` — package installation (may require user confirmation)
- `rm -rf` — destructive (reject unless clearly scoped)
- `eval` / `exec` — dynamic execution (high risk)

If the audit finds concerning patterns, report them to the user before proceeding.
For skills that only use file I/O and standard libraries, the audit passes cleanly.

### 4. Check for referenced files

SKILL.md often references `references/`, `scripts/`, or `templates/` subdirectories.
Extract the list:

```bash
grep -oP 'references/[^`"\s)]+|scripts/[^`"\s)]+|templates/[^`"\s)]+' /tmp/<skill-name>/SKILL.md | sort -u
```

Download referenced files using the same `curl` pattern:

```bash
for f in <list>; do
  curl -sL --max-time 20 -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/<owner>/<repo>/contents/$f?ref=<branch>" \
    -o /tmp/<skill-name>/$f
  python3 -c "
import json, base64
with open('/tmp/<skill-name>/$f') as fh: data = json.load(fh)
content = base64.b64decode(data['content']).decode('utf-8')
with open('/tmp/<skill-name>/$f','w') as fh: fh.write(content)
"
done
```

### 5. Check Python dependencies

If the repo has `pyproject.toml` or `requirements.txt`, check what's needed:

```bash
gh api repos/<owner>/<repo>/contents/pyproject.toml --jq '.content' | base64 -d | grep -A 20 'dependencies'
```

Report dependencies to the user. Core skill functionality (file operations) usually
works without extra packages; research/analysis toolkits often need `openai`, `requests`, etc.

### 6. Install to skills directory

Determine the target path. For skills with a category in the frontmatter:

```bash
mkdir -p ~/.hermes/skills/<category>/<skill-name>/
cp /tmp/<skill-name>/SKILL.md ~/.hermes/skills/<category>/<skill-name>/
```

For uncategorized skills:

```bash
mkdir -p ~/.hermes/skills/<skill-name>/
cp /tmp/<skill-name>/SKILL.md ~/.hermes/skills/<skill-name>/
```

Copy referenced files:

```bash
for dir in references scripts templates; do
  if [ -d "/tmp/<skill-name>/$dir" ]; then
    cp -r "/tmp/<skill-name>/$dir" ~/.hermes/skills/<category>/<skill-name>/
  fi
done
```

### 7. Verify and clean up

```bash
ls -lh ~/.hermes/skills/<category>/<skill-name>/
rm -rf /tmp/<skill-name>/
```

Report: installed path, file count, size, and any dependencies noted.

## Pitfalls

- **GitHub network from China**: `git clone` often times out or gets 502. `curl` to the GitHub REST API is the most reliable method — works even without `gh` auth (60 req/hr unauthenticated rate limit).
- **`gh auth token --git-token` is DEPRECATED** (gh 2.45.0+): Use `gh auth token` without `--git-token`. If `gh` auth is broken (expired keyring token), fall back to unauthenticated `curl` — it works fine for public repos.
- **`ghproxy.com` may not resolve**: Don't assume proxy is available. Try direct first.
- **SKILL.md may not be at the root**: Skill collections (superpowers-zh, etc.) store skills under `skills/<name>/SKILL.md`. Always check the repo tree if root SKILL.md is missing.
- **Default branch is not always `main`**: Check via `gh api repos/<owner>/<repo>` or the REST API for `default_branch`. Some repos use `master`.
- **Large SKILL.md files** (1000+ lines): These are normal for feature-rich skills. Don't skip installation because of file size.
- **Scripts are optional**: Most skills work with just SKILL.md + references. Python scripts (health checks, bootstrappers) are bonus features — note them but don't block installation on missing scripts.
- **Never stage backups inside `~/.hermes/skills/`**: a directory such as
  `skills/<name>.bak.<ts>/` still contains a SKILL.md and gets loaded as its
  own broken skill. Keep backups in `~/.hermes/skill-backups/` (anywhere
  outside `skills/`).
- **A repo may ship a `SHA256SUMS.txt`**: when present, always `sha256sum -c`
  the CLI scripts after download. It turns "the download probably worked" into
  proof, and it is what the skill's own SKILL.md tells the agent to check
  before first use.
- **Check for existing skill first**: If a similar skill already exists locally, compare capabilities before installing. They can coexist if they serve different use cases.
- **`execute_code` blocked in cron mode**: Cron jobs cannot use `execute_code`. Download skills via `terminal` + `curl` instead.

## When to recommend installation

- Skill fills a gap the user has explicitly mentioned
- Skill adds significant capability over what's already installed
- User's use case matches the skill's target domain
- Security audit passes clean

## When to skip

- Skill duplicates existing functionality without meaningful improvement
- Requires complex setup (multiple API keys, system-level installs)
- Security audit finds unresolvable issues
- Skill is abandoned (no commits in 6+ months, broken dependencies)

## See also

- `references/skill-scan-troubleshooting.md` — troubleshooting the `top-hermes-skills.py` scan script (gh CLI deprecations, auth failures, cron mode restrictions)
