---
name: write-a-skill
description: Create new agent skills with proper structure, progressive disclosure, and bundled resources.
---

# Writing Skills

## Process

1. **Gather requirements** - ask user about:
   - What task/domain does the skill cover?
   - What specific use cases should it handle?
   - Does it need executable scripts or just instructions?
   - Any reference materials to include?

2. **Draft the skill** - create:
   - SKILL.md with concise instructions
   - Additional reference files if content exceeds 500 lines
   - Utility scripts if deterministic operations needed

3. **Review with user** - present draft and ask:
   - Does this cover your use cases?
   - Anything missing or unclear?
   - Should any section be more/less detailed?

## Skill Structure

```
skill-name/
├── SKILL.md           # Main instructions (required)
├── references/        # Reference docs, APIs, cheat sheets (optional)
├── scripts/           # Executable tools (optional)
└── templates/         # Templates for output (optional)
```

## SKILL.md Format

```yaml
---
name: my-skill
description: "One-line description: triggers, outcome."
version: 1.0.0
author: You
license: MIT
platforms: [linux, macos, windows]
dependencies: [tool1, tool2]
prerequisites:
  env_vars: [API_KEY]
  commands: [jq, curl]
metadata:
  hermes:
    tags: [tag1, tag2]
---
# Skill Title

## Overview
Brief explanation of what this skill does and when to use it.

## Prerequisites
Tools, env vars, credentials needed.

## Workflow
Numbered steps with exact commands.

## Verification
How to confirm success.
```

## Quality Checklist

- [ ] Frontmatter with name, description, version
- [ ] Clear "when to use this skill" section
- [ ] Concrete examples with copy-paste commands
- [ ] Prerequisites section (dependencies, env vars)
- [ ] Verification steps (how to confirm it worked)
- [ ] Pitfalls / troubleshooting section
- [ ] No placeholder text or TODOs

## Related References

- `references/install-from-directory.md` — How to scan, evaluate, and install skills from a third-party directory (bulk-import workflow)
