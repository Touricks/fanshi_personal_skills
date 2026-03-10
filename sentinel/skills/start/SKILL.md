---
name: start
description: Bootstrap a new project with PRD, ARCHITECTURE, and CLAUDE.md through guided interview. Use when the user says "start", "init project", "set up project", "bootstrap", "new project", or when no PRD.md/ARCHITECTURE.md exists. Produces PRD.md → ARCHITECTURE.md → CLAUDE.md → progress.yaml, then hands off to /routing.
---

# Start — Project Bootstrap Skill

## Overview

Uses a 6-module framework to progressively transform a vague project idea into a complete set of bootstrap documents. Adapted from the prompt-architect 8-module pattern.

Without these documents, the Sentinel maintenance pipeline cannot operate:
- §4.2 compaction needs ARCHITECTURE.md as output target
- §4.3 routing needs PRD.md to judge which tools are relevant
- §4.4 chain-triggers need directory CLAUDE.md to sync against

## Language Behavior

Default to English. If the user writes in Chinese, respond in Chinese. Match the user's language throughout the session.

## 8-Module Framework

| # | Module | Core Question | Output Target |
|---|--------|---------------|---------------|
| 1 | Project Identity | What is this? Who is it for? What problem does it solve? | PRD.md §1 |
| 2 | Core Requirements | What must it do? Priority? Acceptance criteria? | PRD.md §2-3 |
| 3 | Use Cases | What are the key user flows? Happy path + edge cases? | PRD.md §4 |
| 4 | Assumptions & Dependencies | What do we assume to be true? What do we depend on? | PRD.md §5 |
| 5 | Constraints & Non-Goals | What is out of scope? Known limitations? Risks? | PRD.md §6 |
| 6 | Tech Stack | What languages, frameworks, external services? | ARCHITECTURE.md §1 |
| 7 | Architecture & Module Boundaries | How are components organized? | ARCHITECTURE.md §2-3 |
| 8 | Development Workflow & Quality | How does the team work? What standards? | CLAUDE.md rules |

**Optional module (ask only if applicable):**

| # | Module | Core Question | Output Target |
|---|--------|---------------|---------------|
| M | Metrics & Targets | What quantifiable success looks like? | PRD.md §7 |

Applicability: skip for research prototypes / personal experiments. Ask for production apps / team projects.

## Process

### Phase 1: Intake and Quick Diagnosis

#### Sentinel-Aware Scanning

Before scanning, check for `.sentinel/manifest.json`:
- If found: read the `sentinel_owned` and `start_scan_excluded` arrays
- **Exclude all listed paths from the diagnostic scan** — these are pre-installed Sentinel SDK infrastructure (tests, docs, manifests), NOT the user's project
- Do NOT infer project identity, tech stack, or architecture from excluded paths
- `.sentinel/` and `.claude/` are always excluded (framework internals)
- If `.sentinel/manifest.json` does not exist: scan everything (non-Sentinel project)

This ensures `/start` sees a clean slate in Sentinel-initialized projects while still detecting user-created files correctly.

#### File Detection

Read existing project files (respecting exclusions above) to detect what already exists:
- `PRD.md` — if exists, this is an UPDATE, not a fresh start
- `ARCHITECTURE.md` — if exists, preserve and update
- `CLAUDE.md` — if exists, preserve human rules
- `progress.yaml` — if exists, preserve constraints
- `README.md` — may contain project context (skip if in `sentinel_owned`)
- `docs/` — may contain design documents (skip sentinel-owned paths within)
- Source code directories — may indicate existing architecture (skip `.sentinel/`, `.claude/`)

Output a diagnostic table:

```
## Project Bootstrap Diagnostic

| # | Module | Status | Findings |
|---|--------|--------|----------|
| 1 | Project Identity | Partial | README.md mentions "HCI research project" but no formal scope |
| 2 | Core Requirements | Missing | No PRD or requirements document found |
| 3 | Use Cases | Missing | No user flows documented |
| 4 | Assumptions & Dependencies | Missing | No assumptions listed |
| 5 | Constraints & Non-Goals | Missing | No non-goals documented |
| 6 | Tech Stack | Covered | Python files detected, no framework declarations |
| 7 | Architecture | Partial | Directory structure exists but no ARCHITECTURE.md |
| 8 | Workflow & Quality | Partial | CLAUDE.md has some rules, no testing/CI conventions |
| M | Metrics (optional) | N/A | Research prototype — metrics not applicable |
```

Status criteria:
- **Covered**: Sufficient information exists in project files
- **Partial**: Some information exists but incomplete
- **Missing**: Not documented anywhere

### Phase 2: Applicability Assessment

Not every module needs full elicitation. Assess based on project maturity:

| Project State | Typical Approach |
|---------------|-----------------|
| Empty directory | Full 8-module interview |
| Existing code, no docs | Extract from code first, label items as **inferred** vs **confirmed**, run confirmation pass with user |
| Existing docs, incomplete | Fill gaps only |
| Full docs, re-bootstrap | Validate and update |

Use AskUserQuestion to confirm assessment:

```
I've analyzed your project. Here's what I found and what's missing.
[diagnostic table]

I recommend focusing on modules [X, Y, Z]. Does this match your priorities?
Also — is there any context I should know that isn't in the files?
```

### Phase 3: Module-by-Module Completion

For each module with status "Missing" or "Partial", use AskUserQuestion to fill gaps.

**Question priority** (highest to lowest):

1. **Module 1 — Project Identity** (everything else depends on this)
2. **Module 2 — Core Requirements** (defines what the project must do)
3. **Module 3 — Use Cases** (makes requirements concrete and testable)
4. **Module 4 — Assumptions & Dependencies** (surfaces hidden premises)
5. **Module 5 — Constraints & Non-Goals** (prevents scope creep)
6. **Module 6 — Tech Stack** (constrains architecture choices)
7. **Module 7 — Architecture** (module boundaries)
8. **Module 8 — Workflow** (generates CLAUDE.md rules)
9. **Module M — Metrics** (optional, only for production/team projects)

**Questioning strategy:**
- Maximum 4 questions per round (AskUserQuestion limit)
- Each question provides 2-4 options plus custom
- If user says "you decide" or "not sure", suggest a reasonable default and confirm
- When answers are vague, use **example-driven follow-ups** ("Can you give me an example of how a user would do X?")
- After each round, update diagnostic table

**Quality gate before finalizing PRD:**
- Each requirement must have: actor + action + acceptance criterion
- If any requirement lacks acceptance criteria, ask a follow-up
- If overall confidence is low, output "Draft PRD" (not "Final PRD") and list unresolved questions

**Module-specific question templates:**

#### Module 1 — Project Identity
- "Describe your project in one sentence" — Open-ended
- "What problem does this project solve? For whom?" — Open-ended
- "Who is the primary user?" — Options: Developer / End user / Research audience / Internal team
- "What is the project scope?" — Options: Library/toolkit / Web application / CLI tool / Research prototype / Other

#### Module 2 — Core Requirements
- "List 3-5 things this project MUST do" — Open-ended
- "Which of these are MUST-have vs SHOULD-have vs COULD-have?" — Prioritization (MoSCoW)
- "What is the primary deliverable?" — Options: Working software / Research paper + prototype / API / Documentation + templates
- "What does 'done' look like for v1?" — Open-ended

#### Module 3 — Use Cases
- "Describe the main user flow (happy path): user does X → system does Y → outcome Z" — Open-ended
- "What could go wrong? Any edge cases to handle?" — Open-ended
- "For each MUST requirement, what is the acceptance test?" — One per requirement

If user gives minimal answers, propose use cases based on requirements and ask for confirmation.

#### Module 4 — Assumptions & Dependencies
- "What do you assume to be true that, if wrong, would change the approach?" — Open-ended
  - Examples: "OAuth provider supports refresh tokens", "Data fits in memory", "Users have modern browsers"
- "What external systems does this project depend on?" — Open-ended
  - Examples: PostgreSQL, third-party APIs, specific OS, specific hardware
- "Any dependency that might change or become unavailable?" — Open-ended

Label each item as **confirmed** (verified) or **assumed** (needs validation). Assumed items are candidates for future progress.yaml verification.

#### Module 5 — Constraints & Non-Goals
- "What is explicitly OUT of scope for v1?" — Open-ended
- "Any known technical limitations?" — Options: No auth needed / No real-time / No mobile / Other
- "Any risks that could derail the project?" — Open-ended (merge risks into constraints as "constraint that might appear")

#### Module 6 — Tech Stack
- "Primary language?" — Options: Python / TypeScript / Go / Rust / Other
- "Key frameworks or libraries?" — Open-ended (suggest based on project type)
- "External services or APIs?" — Options: Database / Cloud APIs / MCP servers / CLI tools / None
- "Package manager?" — Options: pip/uv / npm/bun / cargo / Other

#### Module 7 — Architecture
Based on confirmed requirements, use cases, and tech stack, PROPOSE an initial architecture:
- Module breakdown (top-level directories and their responsibilities)
- Key interfaces between modules
- Data flow overview

Ask user to confirm, modify, or reject the proposal.

#### Module 8 — Workflow & Quality
- "Testing approach?" — Options: Unit tests required / Integration tests / Manual testing / TDD
- "Code style preferences?" — Open-ended (or extract from existing CLAUDE.md)
- "Any tools or conventions the AI agent should always follow?" — Open-ended
- "Commit/PR workflow?" — Options: Direct to main / Feature branches / PR required

#### Module M — Metrics (optional)
Ask ONLY if project is production/team-facing. Skip for research prototypes.
- "What does success look like, quantitatively?" — Open-ended
- "Any performance targets?" — Options: Response time / Throughput / Availability / Not applicable
- "Current baseline for comparison?" — Open-ended or "N/A (greenfield)"

### Phase 4: Generate Documents

Once all applicable modules reach "Covered", generate the bootstrap documents.

#### 4a. PRD.md

Use `status: draft` if quality gate found unresolved questions. Use `status: v1.0` if all requirements have acceptance criteria.

```markdown
---
project: {name}
version: v1.0          # or "draft" if quality gate has unresolved items
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
---

# {Project Name} — Product Requirements Document

## 1. Project Identity
- **Name**: {name}
- **Problem statement**: {what problem this solves, from Module 1}
- **Target user**: {user}
- **Scope**: {scope}

## 2. Core Requirements

| # | Requirement | Priority | Acceptance Criteria |
|---|-------------|----------|---------------------|
| R1 | {requirement} | MUST | {testable criterion} |
| R2 | {requirement} | SHOULD | {testable criterion} |
| R3 | {requirement} | COULD | {testable criterion} |

## 3. Deliverables
- **Primary deliverable**: {from Module 2}
- **v1 definition of done**: {from Module 2}

## 4. Key Use Cases

### UC1: {use case name}
**Actor:** {who}
**Flow:** {step 1 → step 2 → outcome}
**Edge cases:** {what could go wrong}

### UC2: {use case name}
...

## 5. Assumptions and Dependencies

### Assumptions (must remain true for this approach to work)
| # | Assumption | Status | Impact if wrong |
|---|-----------|--------|-----------------|
| A1 | {assumption} | assumed | {consequence} |
| A2 | {assumption} | confirmed | {consequence} |

### Dependencies (external systems this project relies on)
| # | Dependency | Version/Constraint | Risk if unavailable |
|---|-----------|-------------------|---------------------|
| D1 | {system} | {version} | {impact} |

## 6. Constraints and Non-Goals

### Non-Goals (explicitly out of scope for v1)
{From Module 5}

### Known Limitations
{From Module 5}

### Risks
{From Module 5 — constraints that might appear in the future}

## 7. Metrics and Targets (optional)

{Only if Module M was applicable. Otherwise: "N/A — research prototype / personal project."}

| Metric | Baseline | Target |
|--------|----------|--------|
| {metric} | {current or N/A} | {target} |

## 8. Success Criteria
{Derived from requirements acceptance criteria + metrics if applicable}

## Changelog
| Version | Date | What changed | Why |
|---------|------|-------------|-----|
| v1.0 | {date} | Initial PRD | Project bootstrap via /start |

## Unresolved Questions
{List any items that could not be resolved during the interview. Only present if status is "draft".}
```

#### 4b. ARCHITECTURE.md

```markdown
# {Project Name} — Architecture

## 1. Tech Stack
- **Language**: {from Module 3}
- **Frameworks**: {from Module 3}
- **External services**: {from Module 3}
- **Package manager**: {from Module 3}

## 2. Module Structure
{From Module 4 — table of top-level directories + responsibilities}

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| src/auth/ | Authentication and authorization | oauth.py, middleware.py |
| ... | ... | ... |

## 3. Data Flow
{From Module 4 — how data moves between modules}

## 4. Constraints
{From Module 5 — technical limitations that affect architecture}
```

#### 4c. CLAUDE.md (root, prescriptive rules)

```markdown
# {Project Name}

Architecture and stack: see ARCHITECTURE.md
Requirements: see PRD.md

## Rules
{From Module 6 — testing, style, conventions}
{From existing CLAUDE.md if present — preserve human rules}

## Workflow
{From Module 6 — commit, PR, CI conventions}
```

#### 4d. progress.yaml (machine-readable intake funnel)

```yaml
schema_version: 1
entries:
  - date: "{TODAY'S DATE}"
    title: Project initialized
    status: unprocessed
    session_report: ""
    next_steps:
      - Run /routing to select project tools
    candidates: []
```

### Phase 5: Set Up Directory Structure and Activate Sentinel

Based on the architecture from Module 4:
1. Create the module directories listed in ARCHITECTURE.md
2. Create directory CLAUDE.md manifests for each module (AI-managed, initially minimal)
3. Create `review/` directory for review reports
4. Ensure `.claude/skills/` and `.claude/rules/` exist

#### 5a. Install git hooks (automatic)

Run: `bash .sentinel/hooks/install.sh`

This is low-risk and idempotent. Execute without asking.
If `.git/` doesn't exist yet, skip and note: "Hooks will be installed after `git init`."

#### 5b. Backfill YAML front matter for existing source files (requires confirmation)

Scan the project for `.py`, `.ts`, `.js`, `.sh` files without YAML front matter.
If found:
- Show summary: "Found N source files without YAML headers. Shall I add front matter?"
- Use AskUserQuestion to confirm
- If approved: generate headers for each file (`input`/`output`/`pos`/`last_modified`)
- If declined: skip, note in progress.yaml as a future task

#### 5c. Create directory manifests for existing code directories (requires confirmation)

Scan the project for directories containing source files but no `CLAUDE.md`.
If found:
- Show summary: "Found N directories without manifests. Shall I create them?"
- Use AskUserQuestion to confirm
- If approved: generate directory `CLAUDE.md` for each
- If declined: skip

### Phase 6: Confirm Activation

Tell the developer:
- PRD.md, ARCHITECTURE.md, CLAUDE.md, progress.yaml are ready
- Directory structure is created
- Git hooks are installed (soft warnings on commit)
- [If backfill was done] N source files now have YAML front matter
- [If manifests were created] N directory manifests created
- Chain-trigger pipeline is now active (auto-updates headers and manifests on code changes)
- **Next step: run `/routing`** to scan available tools and select what this project needs
- After routing: run `/boundary` to generate boundary declarations

Sentinel is now operational. All maintenance pipelines are active.

## If Updating Existing Documents

- **PRD.md exists**: Show diff of proposed changes, ask for confirmation before overwriting
- **ARCHITECTURE.md exists**: Merge new information, preserve existing module descriptions
- **CLAUDE.md exists**: NEVER overwrite human rules; only append new rules from Module 6 at the end
- **progress.yaml exists**: NEVER modify; constraints are sacred

## Anti-Patterns

| Do Not | Do Instead |
|--------|-----------|
| Generate PRD without asking the user | Interview first, generate from answers |
| Assume architecture from project name alone | Ask about requirements + use cases before proposing architecture |
| Overwrite existing CLAUDE.md rules | Preserve and append |
| Skip Module 5 (constraints) | Non-goals prevent scope creep — always ask |
| Skip Module 4 (assumptions) | Unchecked assumptions are the #1 source of context degradation |
| Generate all docs before user confirms architecture | Propose architecture in Module 7, wait for confirmation |
| Propose architecture without knowing tech stack | Module 6 before Module 7, always |
| Accept vague requirements without acceptance criteria | Use example-driven follow-ups to make them testable |
| Treat code-extracted info as confirmed | Label as **inferred**, run confirmation pass with user |
| Output "Final PRD" when questions are unresolved | Use "Draft PRD" with Unresolved Questions section |
| Force Module M (Metrics) on research projects | Skip unless production/team project |
