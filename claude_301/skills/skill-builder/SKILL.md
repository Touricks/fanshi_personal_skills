---
name: skill-builder
description: >
  Build a new skill from idea to working SKILL.md. Orchestrates intent capture,
  frontmatter design decisions (execution context, tool permissions, arguments),
  directory scaffolding, and content authoring. Supports quick builds (scaffold +
  design guidance) and full builds (interview + design + scaffold + test/iterate
  via skill-creator). Use when the user says "build skill", "create skill", "new
  skill", "scaffold skill", "make a skill", "I want to build a skill", "add a
  skill", or wants to go from idea to working skill.
  For improving or testing an existing skill, invoke skill-creator directly.
  For agent-level tool boundaries (allowlist/blocklist), see agent-tool-allocation.
---

# Skill Builder

Single entry point for building a new skill within `skillsBuilder/claude_301/skills/`. Combines intent capture, frontmatter design, scaffolding, and optional test-iterate into one workflow.

---

## Build Mode

Before starting, determine the user's intent:

- **Quick build** — "I know what I want." Lightweight intent capture, design decisions, scaffold, refine. No testing.
- **Full build** — "Give me the full treatment." Interview via `skill-creator`, thorough design, scaffold, refine, test-evaluate-iterate.
- **Improve existing** — "I already have a skill." Skip to invoking `skill-creator` pointed at the existing skill's path.

Default to quick build if ambiguous. The user can upgrade to full build at any point.

---

## Phase 1: Capture Intent

**Quick build** — Ask three focused questions:
1. What should this skill enable Claude to do?
2. When should this skill trigger? (user phrases, contexts)
3. What's the expected output format?

**Full build** — Invoke `skill-creator` and follow its "Capture Intent" and "Interview and Research" sections. Once intent is captured and confirmed by the user, return here for Phase 2.

From the answers, derive:
- **skill_name**: kebab-case, hyphens only (no underscores)
- **skill_description**: one-line with trigger phrases ("Use when the user says...")
- **subdirs**: `scripts/` (if automation needed), `resources/` (if reference data), `templates/` (if file generation)

---

## Phase 2: Design Frontmatter

Implement after Phase 1 completed. Revise generated skills.
Walk through each decision. Read the referenced resource file only when the user needs detailed guidance — don't load them unconditionally.

### 2a. Execution Context

Ask: "Will this skill produce large intermediate output or run exploratory tasks?"

- If yes → `context: fork` (isolated sub-agent with own token budget)
- If no → leave as inline (default)
- If unsure → read `resources/context-fork-tools.md` (Parts 1-3) for the decision tree

### 2b. Tool Permissions

Ask: "What tools does this skill need? Read-only, code modification, or shell commands?"

- Read-only → `allowed-tools: [Read, Grep, Glob]`
- Code modification → add `Edit`, `Write`
- Shell commands → use patterns like `Bash(npm:*)`
- **Important**: in fork mode, unlisted tools are silently denied. In inline mode, they prompt the user.
- If unsure → read `resources/context-fork-tools.md` (Parts 5-6) for tool string syntax

### 2c. Arguments

Ask: "Does this skill accept user input?"

- If no arguments needed → skip
- If named parameters → define `arguments` field and `argument-hint`
- If multi-mode → use first argument as mode selector
- If free-form → use `$ARGUMENTS` in the body
- If unsure → read `resources/argument-hint-routing.md` for substitution patterns and pitfalls

### 2d. Agent Tool Boundaries (conditional)

Only ask if the skill spawns sub-agents or chose `context: fork`:
"Does this skill need agent-level tool boundaries beyond `allowed-tools`?"

- If yes → invoke standalone `agent-tool-allocation` skill for allowlist/blocklist guidance
- If no → skip

Record all choices for Phase 3.

---

## Phase 3: Scaffold

Follow the scaffolding procedure in `resources/scaffolding.md`:

1. Validate the skill name (kebab-case, no underscores, no collision with existing skills)
2. Create the directory: `skillsBuilder/claude_301/skills/{skill_name}/`
3. Create any requested subdirs (`scripts/`, `resources/`, `templates/`)
4. Read `templates/skill_template.md` from this skill's base directory
5. Replace placeholders (`{{skill_name}}`, `{{skill_description}}`, `{{skill_title}}`, etc.)
6. Apply design decisions from Phase 2 to the frontmatter:
   - Add `context: fork` if chosen
   - Add `allowed-tools` list if chosen
   - Add `arguments` and `argument-hint` if chosen
7. Write the populated SKILL.md

---

## Phase 4: Refine

Edit the generated SKILL.md to replace scaffold placeholders with real content:

- Fill in workflow steps with the skill's specific logic
- Add domain-specific instructions, output format, examples
- If the skill uses `scripts/`, `resources/`, or `templates/`, create those files now
- Review the complete SKILL.md with the user for immediate feedback

---

## Phase 5: Test and Iterate (optional)

For full builds, or when the user requests it after a quick build:

Invoke `skill-creator` for its test-evaluate-iterate loop. This includes:
- Writing 2-3 realistic test cases
- Running with-skill and baseline comparisons
- Grading, benchmarking, and launching the eval viewer
- Collecting user feedback and improving the skill
- Optionally optimizing the description for triggering accuracy

The orchestrator hands off entirely to `skill-creator` at this point.

---

## Rules

- Always create skills under `skillsBuilder/claude_301/skills/`, never under `.claude/skills/`
- Skill names must be kebab-case with **hyphens only** — underscores are not allowed
- The `description` frontmatter must include trigger phrases — this is how Claude matches skills to user intent
- Only load resource files when the user actually needs detailed guidance — keep context lean
- Do not create `scripts/`, `resources/`, or `templates/` subdirs unless the user specifically requests them

---

## See Also

- **skill-creator** — Full lifecycle: interview, draft, test, evaluate, iterate, optimize description
- **agent-tool-allocation** — Agent-level tool boundaries: allowlist/blocklist, tool_choice, agent schemas
