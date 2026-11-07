# Memory consolidation (Hindsight-inspired)

Pattern for keeping the built-in persistent memory (MEMORY.md / USER.md) fresh, non-duplicative, and evidence-backed. Derived from the vectorize-io/hindsight design: layered memory types, separate retain/recall/reflect operations, observation consolidation with proof chains, and pre-computed mental models. The built-in memory tool is flat text with a hard character budget, so the value is in the *maintenance discipline*, not in a vector DB.

## When to use
- The built-in memory is at or near its char limit (the memory tool reports usage like `98% — 3,921/4,000 chars`).
- A recurring fact keeps going stale (IP changed, port moved, model renamed) and old entries contradict new ones.
- You want a scheduled job to keep memory tidy without relying on in-session ad-hoc edits.

## Standing rules (apply to every memory write, not just the cron job)
1. **Refine, don't overwrite.** When a fact changes, keep the old value as a one-line history note: `old -> new (reason)`. Deleting the old value loses the provenance a future session may need. A bare replacement is the failure mode.
2. **Attach a date/source to new entries.** Format: `fact (YYYY-MM-DD source)`. Without this, staleness is undetectable and the next consolidation pass can't tell what's fresh.
3. **Mark stale entries actively.** When you discover an entry contradicts current state, either fix it in place or flag it (`STALE:` prefix) so the next pass cleans it. Don't silently leave contradictions.
4. **Respect the hard budget before adding.** The memory tool rejects an add that would overflow, then returns `current_entries`. Free room by patching/shortening or merging a stale entry in the *same* operations batch as the add — the limit is checked on the final result, so one batch can remove + add atomically. An add alone that overflows is a guaranteed refusal.

## The consolidation job (recommended: weekly cron)
A durable cron job is the durable version of "remember to tidy memory". It runs in a fresh session with no chat context, so the prompt must be fully self-contained and the mission explicit.

Create via cronjob_manage (action=create). Key knobs:
- `schedule`: a weekly cadence, e.g. `saturday at 17:30`. Place it *after* the existing weekly backup job so a clean backup precedes any memory mutation.
- `continuity: true` — each run sees its own previous output, so it dedupes and works incrementally instead of re-deriving the whole diff from scratch.
- `deliver`: origin (default) so the weekly change-report lands back in the chat that created it.
- `skills`: [] — do NOT bind an unrelated skill (e.g. an Obsidian/note-taking skill) to a memory job. The job needs only the built-in memory tool and session_search. Binding a topical skill just to have one is a foot-gun; an empty skills list is correct here.

Self-contained prompt shape (the job cannot ask the user anything):
1. **Scan the last 7 days** with session_search; focus on user-stated preferences/corrections, newly discovered environment facts (IPs/ports/paths/account shapes), pitfalls hit, project state changes, rejected approaches and why.
2. **Extract with an explicit mission.** Extract: preferences, decisions, pitfalls, environment facts, state changes, tool tips. Ignore: chit-chat, one-off task detail, code itself (it lives in the repo), anything already captured in a skill. A vague "remember things" produces noise.
3. **Diff against current memory + skills.** Merge duplicates; for contradictions, update by refinement (rule 1); for genuinely new facts, add with date/source (rule 2). Check char budget first (rule 4).
4. **Skill check.** For any skill actually used this week, patch stale steps/commands in place and leave a struck-through old line (`~~old rule~~ (superseded by X, date, reason)`) rather than deleting it.
5. **Emit a weekly report**: N added / N updated / N removed / N skills changed, one line each. If nothing changed, say so explicitly ("本周记忆库无需变更") — a no-op is a valid outcome and should be reported, not fudged.

Constraints to put in the prompt: uncertain facts are NOT written (under-record rather than record wrong); all delivered text in Chinese (user requirement); the memory budget is enforced and adds must batch with the room-frees; end with one-line conclusion.

## First-run verification
After creating the job, fire it once with cronjob_manage action=run to validate the prompt end-to-end (it runs in background and posts its report back). A created-but-never-fired cron prompt can contain a self-reference or tool gap that only a real run exposes. Review the first report for over-aggressive edits before trusting the weekly cadence.

## Mapping to Hindsight concepts
| Hindsight | Built-in memory equivalent |
|-----------|----------------------------|
| retain (mission-driven extraction) | the weekly scan+extract mission in the cron prompt |
| observation consolidation + proof chain | refine-don't-overwrite rule + date/source on entries |
| mental models (pre-computed, incrementally rewritten) | USER.md / SOUL.md, maintained by hand as dimensional sections, patched not rewritten |
| freshness tracking | the continuation output + STALE marking; vector retrieval is NOT needed at this scale (a few hundred entries) — FTS5 session_search + manual review suffices. Reconsider only if entries grow into the thousands. |
