# ghproxy.net Usage Patterns (China Network)

`ghproxy.net` (and mirrors like `mirror.ghproxy.com`) is a GitHub release/content proxy
for mainland China. It wraps GitHub URLs so they resolve properly when
`raw.githubusercontent.com` is DNS-polluted (resolves to `0.0.0.0`).

## Available mirrors

```bash
ghproxy.net              # primary, most reliable
mirror.ghproxy.com       # backup
gh.api.99988866.xyz      # backup
```

## Pattern: Download raw file from GitHub

```bash
curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/branch/path/file"
```

## Pattern: Clone/Pull via mirror

```bash
git clone https://ghproxy.net/https://github.com/owner/repo.git
```

Already set in this environment's Git config (see memory).

## Pattern: Hermes skills install

The `hermes skills install` command fetches via skills.sh, which itself fetches from
`raw.githubusercontent.com`. When DNS fails:

### If skills.sh is reachable:

```bash
hermes skills tap add owner/repo          # add source repo
hermes skills install <identifier> --yes  # install by identifier
```

The `--yes` flag skips the interactive confirmation prompt. The internal
security scanner may still block DANGEROUS/CRITICAL verdicts.

### If skills.sh times out or raw.githubusercontent URLs fail:

Fall back to manual install:

```bash
# 1. Download SKILL.md via ghproxy
curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/main/SKILL.md" \
  -o /tmp/skill-name.md

# 2. Verify it's real content (not a Cloudflare/error HTML page)
head -5 /tmp/skill-name.md     # should start with "---\nname: ..."

# 3. Copy to skills directory
mkdir -p ~/.hermes/skills/<skill-name>
cp /tmp/skill-name.md ~/.hermes/skills/<skill-name>/SKILL.md

# 4. Verify it shows in list
hermes skills list | grep <skill-name>
```

## Pattern: Download release assets

```bash
# Instead of:
# curl -sLO "https://github.com/owner/repo/releases/download/v1.0/file.deb"

# Use:
curl -sL "https://ghproxy.net/https://github.com/owner/repo/releases/download/v1.0/file.deb" \
  -o /tmp/file.deb
```

## Verification

After downloading, always check the file is real (not Cloudflare challenge HTML):

```bash
file /tmp/downloaded-file
# Should show: "HTML document" → it's a CF page, not the real file
# Should show: "gzip compressed" / "Debian binary package" / "ASCII text" → real content
head -c 200 /tmp/downloaded-file | grep -q "<!DOCTYPE" && echo "CF CHALLENGE PAGE - retry"
```
