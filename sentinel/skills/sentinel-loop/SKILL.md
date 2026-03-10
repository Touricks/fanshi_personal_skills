---
name: sentinel-loop
description: Propose a Ralph Loop iteration based on current project state. Reads progress.yaml and PRD.md to identify the next task, builds a structured prompt with completion condition, and saves a copy-pasteable /ralph-loop:ralph-loop command. Use when "sentinel-loop", "iterate", "start working", "what's next", or after /boundary completes.
---

# Loop — Context-Aware Development Launcher

Thin orchestrator that bridges Sentinel's documentation system with iterative development via Ralph Loop. Computes configuration, saves command for developer to copy-paste, then STOPS.

## Prerequisites

- Project bootstrapped via `/start` (PRD.md, ARCHITECTURE.md, CLAUDE.md, progress.yaml must exist)
- Ralph Loop plugin (optional but recommended) — `claude plugin install ralph-loop`

## Canonical Command

The Ralph Loop plugin skill invocation is always `/ralph-loop:ralph-loop` (plugin-name:skill-name).
Never emit `/ralph-loop` without the `:ralph-loop` suffix — it is invalid.

## Workflow

### Step 0: Check capabilities and scope

1. Check if the plugin skill `ralph-loop:ralph-loop` appears in the available skills list
   - If not available: warn user to install (`claude plugin install ralph-loop`)
2. Check if PRD.md, ARCHITECTURE.md, progress.yaml, CLAUDE.md exist
   - If any are missing: tell user to run `/start` first, STOP

### Step 1: Read project state

Read the following files:
- **PRD.md** — requirements table with IDs (R1, R2...) and acceptance criteria
- **ARCHITECTURE.md** — module structure, tech stack, data flow
- **progress.yaml** — read the 3 most recent entries (not just latest), looking for:
  - Most recent `next_steps` field
  - Unresolved blockers from recent session reports
- **CLAUDE.md** — read the FULL `## Rules` section (will be injected verbatim)

### Step 2: Resolve next task

Priority chain (do NOT guess):

1. **User argument**: if user provided one (e.g., `/sentinel-loop fix auth bug`), use that as the task
2. **progress.yaml `next_steps`**: if the most recent entry has a non-empty `next_steps` list, propose those
3. **PRD.md unfulfilled requirements**: scan the requirements table for the highest-priority (MUST > SHOULD > COULD) requirement whose acceptance criteria are not yet met, propose it
4. **Ask the user**: if none of the above yield a clear task, use AskUserQuestion: "What would you like to work on?"

### Step 3: Derive scope and boundaries

From the task (Step 2) and architecture (Step 1), determine:
- **Relevant modules** — only directories/files touched by this task (from ARCHITECTURE.md)
- **Boundaries** — what NOT to change (e.g., "Do not modify tests/", "Do not change the API surface of module X")
- **CLAUDE.md Rules** — carry forward `## Rules` from Step 1

### Step 4: Build completion condition and nonce

The completion condition = task-specific criterion + Sentinel maintenance conditions:

1. **Task-specific criterion** — from PRD acceptance criteria or a testable statement
2. All modified files have updated YAML front matter headers
3. All directory CLAUDE.md manifests are consistent with current files
4. progress.yaml updated with session entry (or /progress invoked)
5. Session report generated under docs/sessions/ (via /progress)

Items 2-5 are the **Sentinel maintenance conditions** — always required, referenced by name below.

Produce TWO separate outputs:

1. **Completion condition** — the full compound criteria, e.g.:
   `"Auth bug fixed, all tests pass, YAML headers updated, directory manifests current, /progress logged, session report saved"`

2. **Completion promise nonce** — a unique per-run token for `--completion-promise` and `<promise>` tags.
   Generate as: `SENTINEL_` + requirement ID or task keyword + `_` + 6 random alphanumeric chars.
   Examples: `SENTINEL_R1_K8M3Q2`, `SENTINEL_FIX_A7X9P1`, `SENTINEL_TASK_W2N5J8`

   Do NOT use semantic phrases like `"DONE"` or `"TASK COMPLETE"` — they risk false triggers
   when the model discusses the loop protocol or quotes instructions.

**Max iterations heuristic:**

| Task scope | Suggested iterations |
|------------|---------------------|
| Docs / small refactors | 4-6 |
| Single contained feature or bugfix | 8-10 |
| Cross-cutting implementation | 12-20 |
| Default (if unclear) | 10 |

### Step 5: Assemble launch payload

Using outputs from Steps 2-4, build the prompt from the template below. This payload is:
- the quoted argument passed to `/ralph-loop:ralph-loop`
- saved to `.sentinel/tmp/loop-launch.md` as a copy-pasteable command

#### Payload Template

Use this EXACT structure. Fill in the slots with dynamic content. Do NOT rearrange sections or omit any.

PAYLOAD STRUCTURE (for reference only — do not copy this formatting into loop-launch.md):

> ## Task Objective
> {task description from Step 2}
>
> ## Project Context
> {relevant modules from Step 3}
>
> ## Rules (mandatory — follow exactly)
> {CLAUDE.md ## Rules section from Step 3, injected VERBATIM — do NOT condense, summarize, or rephrase}
>
> ## Sentinel Maintenance Conditions
> Follow all Sentinel maintenance conditions (items 2-5 from Completion Condition). Do NOT modify root CLAUDE.md — it is human-managed.
>
> ## Boundaries
> {boundaries from Step 3}
>
> ## Completion Condition
> {full compound condition from Step 4}
>
> Signal completion by outputting <promise>{nonce from Step 4}</promise> exactly once, only after ALL conditions above are satisfied.
> When referring to the promise protocol before completion, use escaped `<promise>` (in backticks), never raw tags.

#### Shell-safe escaping

Ensure the saved command is shell-safe: escape `\` `` ` `` `"` `$`, normalize CRLF → LF. The payload must not contain triple backticks (breaks ralph-loop's bash parser).

#### Save and validate

Save `.sentinel/tmp/loop-launch.md` (overwrite each time). The file must contain EXACTLY:

/ralph-loop:ralph-loop "{escaped payload}" --max-iterations {N} --completion-promise "{nonce}"

Hard constraints on loop-launch.md content:
- First characters must be `/ralph-loop:ralph-loop ` (never `/ralph-loop ` without `:ralph-loop`)
- No markdown headings (`#`), no code fences, no HTML tags
- No extra sections, labels, or commentary
- Single command only — nothing before, nothing after

Self-check before saving:
- [ ] Starts with `/ralph-loop:ralph-loop "`
- [ ] Contains no triple backticks
- [ ] Contains no markdown headings (`#`)
- [ ] Contains `--completion-promise` and `--max-iterations` flags
- [ ] `<promise>` nonce in body matches `--completion-promise` flag value

After saving, validate:

bash .claude/skills/sentinel-loop/scripts/validate-launch.sh .sentinel/tmp/loop-launch.md

If validation fails, fix the issue and re-save before proceeding.

### Step 6: Handoff

Tell the developer:
- Command saved to `.sentinel/tmp/loop-launch.md`
- Copy the command and paste it into a new Claude Code session to start the loop
- Run `/progress` when the task is complete
- To adjust: tell the agent what to change and it will regenerate

/sentinel-loop STOPS here.

## Anti-patterns

| Do NOT | Why |
|--------|-----|
| Auto-chain into another loop after completion | Runaway risk, silent scope creep |
| Condense or rephrase CLAUDE.md rules | Omission of hard constraints |
| Invoke /sentinel-loop recursively from within a ralph-loop | Infinite nesting |
| Guess the next task when no clear signal exists | Waste model judgment — ask the user instead |
| Use semantic phrases like "DONE" as `--completion-promise` | Risk false triggers when model discusses protocol; use a per-run nonce like `SENTINEL_R1_K8M3Q2` |
