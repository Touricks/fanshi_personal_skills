---
name: routing
description: Scan global skills against project context and produce a tool routing report for developer review. Use when initializing a project, onboarding new tools, or when the developer says "routing", "scan tools", "which skills do I need", "update tool inventory". Produces docs/tool-routing-report.md and STOPS for human approval before any skills are moved.
---

# Routing Skill

Analyze the project context and the full global skill list, then produce a routing report that recommends which skills should be loaded into project scope. **This skill produces a document for human review — it does NOT move or copy any skills.**

## Workflow

### Step 1: Read project context

Read the following files to understand what this project does:
- `CLAUDE.md` (root)
- `ARCHITECTURE.md` or `docs/architecture.md` (if exists)
- `README.md` (if exists)
- `.claude/rules/tool-boundary.md` (if exists — means boundary has run before)
- `docs/tool-routing-report.md` (if exists — means routing has run before; this is an UPDATE)

### Step 2: Inventory global skills

Collect the full skill list from the current session's system reminder. For each skill, extract:
- Name
- Source (plugin / local / npx / MCP)
- One-line description

### Step 3: Classify each skill

For each global skill, determine:
- **Include**: clearly relevant to this project's tech stack, workflow, or domain
- **Exclude**: irrelevant to this project
- **Uncertain**: might be useful but unclear — flag for developer decision

Provide a one-sentence rationale for each classification.

### Step 4: Generate or update `docs/tool-routing-report.md`

If the file already exists, update it (preserve developer notes from previous reviews, update the skill inventory and classifications). If it does not exist, create it.

Use this structure:

```markdown
---
generated_at: {YYYY-MM-DD}
project: {project name from CLAUDE.md or directory name}
status: pending_review  # pending_review | approved | needs_revision
total_skills_scanned: {count}
skills_included: {count}
skills_excluded: {count}
skills_uncertain: {count}
---

# Tool Routing Report

## Included Skills

| Skill | Source | Rationale |
|-------|--------|-----------|
| call-codex | user:skill | Project uses Codex for second opinions (see side_effect/codex_cli_usage.md) |
| ... | ... | ... |

## Excluded Skills

| Skill | Source | Rationale |
|-------|--------|-----------|
| original:latex-posters | plugin | Project is not academic poster work |
| ... | ... | ... |

## Uncertain — Needs Developer Decision

| Skill | Source | Rationale | Developer Decision |
|-------|--------|-----------|-------------------|
| original:pdf | plugin | Project has report docs but unclear if PDF generation needed | |

## Developer Notes

> {Space for developer to add notes during review. Preserved across updates.}

## Appendix: Full Global Skill List

{Complete list of all skills detected in this session, with source and description.}
```

### Step 5: STOP

Tell the developer:
- The report is at `docs/tool-routing-report.md`
- Review the Included/Excluded/Uncertain lists
- Fill in decisions for Uncertain skills
- Mark `status: approved` when ready
- Then run `/boundary` to generate tool boundary declarations

**Do NOT copy or move any skills. Do NOT modify `.claude/skills/` or `.claude/rules/`. This skill only produces the report.**

## If updating an existing report

- Preserve the `## Developer Notes` section
- Preserve any `Developer Decision` entries already filled in
- Update skill inventory (add new skills, remove disappeared ones)
- Re-classify if project context has changed
- Reset `status` to `pending_review` and update `generated_at`
