# Installing Skills from a Third-Party Directory

When a user has a directory of skills (e.g. from a git clone or download) and wants to selectively install them into Hermes, follow this workflow.

## Step 1: Scan for SKILL.md Files

```bash
# Find all SKILL.md in the directory tree
find /path/to/skills-dir -name "SKILL.md"
```

Count them to know the scale:
```bash
find /path/to/skills-dir -name "SKILL.md" | wc -l
```

## Step 2: Compare Against Installed Skills

Use `skills_list()` (the tool, not the shell) to get the full catalogue of currently installed skills.

**Key insight**: The installed list is indexed by skill name (from the `name:` field in SKILL.md frontmatter), not by file path. Cross-reference the `name:` field of each discovered SKILL.md against the installed list.

## Step 3: Categorize New Skills

Group new (uninstalled) skills by category:
- **High value**: Fills a capability gap, solves a real problem the user faces
- **Overlap**: Already covered by an existing installed skill (same name or identical purpose)
- **Niche**: Interesting but requires external tools/environments the user doesn't have
- **Dangerous** (red-teaming, godmode, ablation): Flag these for security review before installing

## Step 4: Present to User

Show a categorized table: skill name → description → why it's useful. Let the user decide which batch to install.

## Step 5: Install via skill_manage(action='create')

For each chosen skill, read its SKILL.md content and recreate it via `skill_manage(action='create')` with the full content. The `create` action only accepts SKILL.md — linked files (references/, scripts/, templates/) must be added separately with `skill_manage(action='write_file')`.

**Copying the entire directory** is the wrong approach — Hermes skills are indexed by the curator, not by filesystem presence.

## Step 6: Security Audit

Per the skill installation rule, every newly installed skill must be audited:

```bash
python ~/.hermes/skills/security/security-audit/scripts/audit_skills.py <skill-name>
```

Or for a quick manual check:
```bash
grep -nri "shell=True\|exec(\|eval(\|os\.system\|rm -rf\|password\|api_key\|secret" ~/.hermes/skills/<name>/
```

## Common Pitfalls

- **Copying files directly** into `~/.hermes/skills/` won't register the skill — the curator indexes by metadata, not file presence. Always use `skill_manage(action='create')`.
- **Linked files** (scripts, references, templates) are NOT copied by `create` — each needs a separate write_file call.
- **Name collisions**: If a skill in the download dir has the same name as an installed skill, DO NOT overwrite. Compare content to decide whether to skip, rename, or merge.
- **Relative paths in SKILL.md**: If the source SKILL.md references `./scripts/foo.py`, you must recreate that file under the new skill's `scripts/` directory. The relative path inside the skill directory is preserved automatically.
- **Bulk install**: Installing 15+ skills is best done in batches of 5 per message to keep tool results manageable.
