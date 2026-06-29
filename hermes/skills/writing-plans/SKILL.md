---
name: writing-plans
description: "Write implementation plans: bite-sized tasks, paths, code."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation]
    related_skills: [subagent-driven-development, test-driven-development, requesting-code-review]
---

# Writing Implementation Plans

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

## Plan Structure

Every plan in `.hermes/plans/` or the project repo should be a markdown file with:

### 1. Requirements Summary

A concise one-paragraph summary of what needs to be built and what success looks like.

### 2. Design Decisions

Key trade-offs and design choices. What approach was taken and why alternatives were rejected. This is NOT an architecture document — just the decisions that affect implementation.

### 3. Implementation Tasks

Each task is numbered, self-contained, and includes:

- **File**: exact path (e.g. `src/lib/data.ts`)
- **What**: what to do, in detail
- **Code**: complete code to write (or at minimum the function signatures and key logic)
- **How to verify**: the exact command(s) the implementer should run

### 4. Verification

How to verify the full feature end-to-end.

### 5. What Not To Do

Common mistakes, pitfalls, and anti-patterns specific to this implementation. Save the implementer from repeating your mistakes.

## File Resolution

When a plan references a file path, try these resolutions in order:

1. Find the file from the project root
2. Search by filename ignoring directory

## Principles

### Bite-Sized Tasks

Each task should take no more than ~20 minutes to implement. If a task needs more, split it. A task should be one logical change.

### Complete Code

Write the actual code in the task description. The implementer should be able to copy-paste and have it work. If the code is too long, write the key functions and leave utility functions as "implement similarly".

### Testing Commands

Every task must include how to test it. The implementer should run the test after completing the task, not after all tasks.

### Frequent Commits

The plan should specify when to commit (after each working task, not after every single file change).
