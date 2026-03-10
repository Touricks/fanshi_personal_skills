---
name: progress
description: Generate a structured progress.yaml session entry with typed Candidates for the compaction promotion pipeline, and optionally a durable session report under docs/sessions/. Use at the end of a session, after completing a task, or when the user says "progress", "log session", "what did we learn", "save lessons". Produces entries that compaction can process into CLAUDE.md (rules) and ARCHITECTURE.md (facts).
---

# Progress — Session Log Entry Generator

Generates a properly-formatted progress.yaml entry with typed candidates that the compaction engine can process. This is the intake funnel for promoting lessons into CLAUDE.md (rules) and ARCHITECTURE.md (facts).

## Why This Matters

progress.yaml is NOT a rule store — it's a machine-readable intake funnel. Lessons stay as free text in session reports unless explicitly typed as candidates. Without typed candidates, the compaction promotion gate has nothing to process, and lessons never reach CLAUDE.md or ARCHITECTURE.md.

```
Session ends → /progress generates entry with candidates
    → Appends to progress.yaml (intake funnel)
    → Optionally generates docs/sessions/ report (durable documentation)
    → Runs compaction CLI → classifies candidates
        → rule candidates → proposed for CLAUDE.md (with approval)
        → fact candidates → proposed for ARCHITECTURE.md (with approval)
    → Marks promoted entries as absorbed
```

## Language Behavior

Default to English. If the user writes in Chinese, respond in Chinese. Match the user's language throughout.

## Workflow

### Step 1: Read session context

Read the following files:
- **progress.yaml** — understand existing entries (avoid duplicating recent content)
- **CLAUDE.md** — understand existing rules (avoid creating candidates that duplicate them)
- Review what was done in this session: files modified, tasks completed, problems encountered

### Step 2: Generate entry metadata

Determine:
- `date`: today's date in YYYY-MM-DD format
- `title`: concise session title (e.g., "Fix auth token refresh")
- `next_steps`: list of concrete next actions

### Step 3: Generate typed candidates

This is the critical step. For each lesson or pitfall from this session, evaluate whether it should become a candidate for promotion.

**Rule candidate** — for reusable prescriptive rules ("always do X", "never do Y"):
```yaml
- id: cand-{date}-{kebab-slug}
  type: rule
  text: {rule text}
  scope: {scope}
  confidence: {confidence}
  needs_approval: {true/false}
  promotion_targets: [CLAUDE.md]
```

Fields:
- `scope`:
  - `global` — project-wide rule (goes to root CLAUDE.md)
  - `module` — directory-level rule (goes to a directory CLAUDE.md)
  - `incident-only` — one-time finding, do NOT promote
- `confidence`:
  - `high` — verified across multiple instances or sessions
  - `med` — seems right based on this session
  - `low` — uncertain, needs more evidence
- `needs_approval`:
  - `true` (DEFAULT) — compaction proposes to CLAUDE.md, human must approve
  - `false` — only for very clear, low-risk rules (auto-promoted by compaction)

**Fact candidate** — for factual discoveries about the codebase ("module X depends on Y"):
```yaml
- id: cand-{date}-{kebab-slug}
  type: fact
  text: {fact text}
  subsystem: {module name}
  confidence: {confidence}
  promotion_targets: [ARCHITECTURE.md]
```

**ID generation**: `cand-{date}-{first-5-words-kebab-case}`. If collision, append `-2`, `-3`.

**Rules for candidate generation:**
- NOT every lesson becomes a candidate. Only genuinely reusable insights.
- Check CLAUDE.md — do NOT create candidates that duplicate existing rules.
- Default to `needs_approval: true` — err on the side of human review.
- `incident-only` scope = "this was a one-time thing, log it but don't promote."
- If no candidates this session, use an empty list: `candidates: []`

### Step 4: Set status

Always set `status: unprocessed`. Compaction will later process this entry, promote candidates, and mark it `absorbed`.

### Step 5: Present entry for review

Show the complete generated YAML entry to the user. Use AskUserQuestion with options:
- "Append to progress.yaml" — write the entry
- "Let me edit first" — user modifies, then re-present
- "Skip" — discard

If approved, append to progress.yaml using the YAML schema. The entry is added to the `entries` list in the file.

### Step 5.5: Generate session report

After the progress.yaml entry is appended, generate a durable session report under `docs/sessions/`. This is a separate artifact from the progress.yaml entry — it serves human readers, not the compaction pipeline.

**1. Build the report.** Filename: `docs/sessions/{YYYY-MM-DD}-{kebab-case-title}.md`
- Kebab-case: lowercase, spaces→hyphens, strip non-alphanumeric. E.g., "Fix Auth Bug" → `fix-auth-bug`
- Same-date collision: append `-2`, `-3` etc. if file already exists
- The date and session title MUST be identical to the progress.yaml entry

**2. Report format:**

```markdown
---
date: {YYYY-MM-DD}
title: {session title}
task_source: {see enum below}
files_changed: {count of changed repo files, excluding progress.yaml and the report itself}
---

# {session title}

## Objective
{What was the goal of this task — 1-3 sentences}

## Changes
{1-3 subsections grouped by feature area or subsystem, not by commit chronology}

### Files Modified
| File | Change |
|------|--------|
| {path} | {brief description of what changed} |

## Decisions
{Key decisions made during this session and their rationale. Omit section entirely if none.}

## Issues and Follow-ups
{Open issues, things to revisit, known limitations. Omit section entirely if none.}
```

**`task_source` enum:**

| Value | Meaning |
|-------|---------|
| `sentinel-loop` | Task launched via /sentinel-loop (Ralph Loop) |
| `prd-requirement` | Task derived from PRD.md requirement ID |
| `progress-next-steps` | Task from previous progress.yaml `next_steps` |
| `user-request` | Ad-hoc task requested directly by developer |

**3. Present the report** via AskUserQuestion:
- "Save session report" — write the file to `docs/sessions/`
- "Skip report" — only keep the progress.yaml entry

If the session changed ≤2 files and involved no architectural decisions (e.g., typo fix, single config change), recommend "Skip report" as the default option.

**4. If saved**, ensure `docs/sessions/` directory exists (create if needed), then write the file. Set `session_report` field in the progress.yaml entry to the report path.

**Key constraints:**
- The report is NOT a reformatted copy of the progress.yaml entry — it serves a different audience
- Never include candidates or status in the report (those belong in progress.yaml only)
- Write a standalone session summary for a human reader: objective, changes, decisions, follow-ups
- Concise: 1-2 pages max

### Step 6: Run Compaction

After progress.yaml entry is appended and session report is handled, run the compaction engine to process candidates.

**The classification logic lives exclusively in `compact.py` — do NOT re-implement or describe promotion rules here.**

**1. Run the compaction CLI:**
```bash
PYTHONPATH=.sentinel python .sentinel/compaction/compact.py --progress progress.yaml
```
Read the JSON output. It contains: `auto_promote_rules`, `suggested_rules`, `architecture_facts`, and `reviewed_entries` (list of `{date, title, has_candidates}` for all unprocessed entries examined).

**2. If no promotable candidates** (all three arrays are empty): skip to step 4b.

**3. Present promotion results** via AskUserQuestion. Show what the compaction engine classified:
- **Auto-promote rules**: "These rules are ready for CLAUDE.md:" (list each)
- **Suggested rules**: "These rules need your review:" (list each)
- **Architecture facts**: "These facts would be added to ARCHITECTURE.md:" (list each)
- Options: "Apply all" / "Select which to apply" / "Skip promotion"

**4a. If approved (fully or partially):**
- Use Edit tool to add approved rules to CLAUDE.md `## Rules` section
- Use Edit tool to add approved facts to the relevant section of ARCHITECTURE.md
- Mark absorbed: for each entry in `reviewed_entries` whose candidates were ALL promoted (or that had `has_candidates: false`), run:
  ```bash
  PYTHONPATH=.sentinel python .sentinel/compaction/compact.py --mark-absorbed "{date}" "{title}" --progress progress.yaml
  ```
- Entries whose candidates were rejected or deferred: leave as `unprocessed`

**4b. If no candidates or all skipped:**
- Entries with `has_candidates: false` in `reviewed_entries` are effectively done — mark them absorbed
- Entries with rejected/deferred candidates: leave as `unprocessed`

**5. Final summary.** Tell the user:
- "Entry added to progress.yaml."
- If session report was saved: "Session report saved to docs/sessions/{filename}."
- If promoted: "N rule(s) added to CLAUDE.md, M fact(s) added to ARCHITECTURE.md."
- "K entry/entries marked absorbed, J remain unprocessed."
- If no candidates across all entries: "No candidates to process."

## Entry Schema

Must match `progress_format.py:parse_progress()` YAML schema:

```yaml
- date: "{YYYY-MM-DD}"
  title: "{session title}"
  status: unprocessed
  session_report: ""
  next_steps:
    - "{what to do next}"
  candidates:
    - id: cand-{date}-{kebab-slug}
      type: rule
      text: "{rule text}"
      scope: "{global/module/incident-only}"
      confidence: "{high/med/low}"
      needs_approval: true
      promotion_targets: [CLAUDE.md]
    - id: cand-{date}-{kebab-slug}
      type: fact
      text: "{fact text}"
      subsystem: "{module name}"
      confidence: "{high/med/low}"
      promotion_targets: [ARCHITECTURE.md]
```

## Anti-Patterns

| Do NOT | Do Instead |
|--------|-----------|
| Make every lesson a candidate | Only promote genuinely reusable insights |
| Set needs_approval=false by default | Default to `true` — human reviews before CLAUDE.md changes |
| Duplicate existing CLAUDE.md rules as candidates | Check CLAUDE.md first |
| Write symptoms as pitfalls in session reports | Write root causes |
| Skip the candidates field | Always include it, even if empty (`candidates: []`) |
| Overwrite existing progress.yaml content | Append to entries list only |
| Use markdown format instead of YAML | The compaction parser expects strict YAML schema |
| Reuse progress.yaml fields as session report content | Write a standalone human-readable summary |
| Include candidates/status in the session report | Those belong in progress.yaml only |
| Generate reports for trivial sessions (≤2 files, no decisions) | Recommend "Skip report" as default option |
| Use different date/title than progress.yaml entry | Both artifacts must share identical date and session title |
