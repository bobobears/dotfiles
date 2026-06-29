---
name: subagent-driven-development
description: "Execute plans via delegate_task subagents (2-stage review)."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, subagent, implementation, workflow, parallel]
    related_skills: [writing-plans, requesting-code-review, test-driven-development]
---

# Subagent-Driven Development

## Overview

Execute implementation plans by dispatching fresh subagents per task with systematic two-stage review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## Process

### Phase 1: Plan and Decompose

1. Read the plan from `.hermes/plans/` (or wherever the user placed it)
2. For each implementation task in the plan, decompose it into sub-tasks that each modify a single file or a logical group of files
3. Group tasks that are independent (no shared state, no sequential dependency) — these can run in parallel
4. Group tasks that depend on each other — these must run sequentially

### Phase 2: Dispatch Subagents

For each independent group:

1. Dispatch via `delegate_task` with:
   - **Goal**: exactly what to build (from the plan task)
   - **Context**: the plan task details + code snippets + test commands
   - **Toolsets**: ['terminal', 'file', 'coding'] for implementation tasks

2. Each subagent executes its task independently:
   - Writes code
   - Runs tests
   - Commits changes (if in a git repo)

### Phase 3: Two-Stage Review

#### Stage 1: Specification Review

Review each subagent's output against the plan:

- Does it implement exactly what was spec'd?
- Are there any deviations from the plan?
- Are tests passing?

#### Stage 2: Quality Review

- Is the code clean and maintainable?
- Are there edge cases not handled?
- Is there proper error handling?
- Are tests comprehensive?

### Phase 4: Integration

- Merge all changes
- Run full test suite
- Verify end-to-end functionality

## Anti-Patterns

- **Don't dispatch one subagent per file** — batch related files into logical tasks
- **Don't skip Stage 1 review** — spec deviations compound fast
- **Don't batch dependent tasks** into the same parallel group
- **Don't give subagents too much context** — keep goals focused and specific
