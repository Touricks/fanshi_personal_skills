---
name: start
description: Bootstrap a new project with CLAUDE.md and PROGRESS.md. Use when the user runs /start, says "initialize project", "set up claude.md", or wants to create the external memory system for a new or existing project. Handles both existing projects (auto-detect and populate) and empty folders (provide guided templates).
---

# /start — Project Bootstrap

## Workflow

### 1. Detect Project State

Scan the current directory for project indicators: package.json, pyproject.toml, Cargo.toml, go.mod, Makefile, Dockerfile, README*, src/, lib/, app/, etc.

- **Has files** → "existing project" mode: read available files to auto-populate CLAUDE.md
- **Empty or near-empty** → "empty folder" mode: generate template with `[TODO: ...]` placeholders

### 2. Generate CLAUDE.md

Create `CLAUDE.md` in the project root with ALL of the following sections.

**In existing-project mode**: fill sections from detected files. Ask the user to confirm or correct.
**In empty-folder mode**: use `[TODO: ...]` placeholders with the guidance comments shown below.

```markdown
# CLAUDE.md

## Project Overview
<!-- 1-2 sentences: what this project does and why it exists -->
<!-- Empty folder: describe the problem you're solving and your approach -->

## Tech Stack
<!-- Languages, frameworks, databases, APIs, key dependencies -->
<!-- Empty folder: list what you plan to use; update as you add deps -->

## Directory Structure
<!-- Key directories and their purposes -->
<!-- Empty folder: define your intended layout BEFORE writing code -->

## Code Conventions
<!-- Naming style, type annotations, docstring policy, commit message format -->
<!-- Suggested commit format: [module] action: description -->
<!-- Empty folder: set rules early — harder to enforce retroactively -->

## Build & Run
<!-- How to install deps, start dev server, run tests -->
<!-- Empty folder: fill in as you set up each step -->

## Hard Rules (Do NOT)
<!-- Absolute prohibitions — Claude will always respect these -->
<!-- At minimum include:
- Do not modify .env files
- Do not install packages outside the project/container
- Do not touch production data -->

## Key Architecture Decisions
<!-- Major design choices that should be respected -->
<!-- Empty folder: document decisions as you make them -->
```

**Important**: CLAUDE.md is a STATIC config. Once written, only update when the project architecture changes significantly. It is NOT a log.

### 3. Create PROGRESS.md

Create `PROGRESS.md` in the project root with this content:

```markdown
# PROGRESS.md

> Dynamic log of what we've done, what went wrong, and what we learned.
> This file is the project's running memory. **Append only — never overwrite.**

## When to Update
- After completing any task
- After encountering and resolving a bug or issue
- After making an architectural decision
- At the end of each work session

## How to Update
- Run `/progress` to auto-generate an entry, or manually append
- Each entry uses this format:

## YYYY-MM-DD
### Completed: [task title]
- What was done

### Pitfalls
- ❌ [problem and root cause, not just symptoms]

### Lessons
- [reusable rule extracted from this session]

### Next Steps
- [what to do next]

---

## [TODAY'S DATE]
### Completed: Project initialized
- Created CLAUDE.md (project config)
- Created PROGRESS.md (dynamic log)

### Next Steps
- [Ask user what they plan to work on first]
```

Replace `[TODAY'S DATE]` with the actual date.

### 4. Post-Setup Reminder

After creating both files, tell the user:

1. `CLAUDE.md` = static project config (update rarely)
2. `PROGRESS.md` = dynamic session log (update after every task)
3. Use `/progress` after each work session to append a new entry
4. Review PROGRESS.md periodically to catch repeated mistakes or stalled progress
