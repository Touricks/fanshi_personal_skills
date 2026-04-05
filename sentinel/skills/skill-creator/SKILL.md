---
name: skill-creator
description: >-
  Analyze an existing skill folder for quality and produce actionable improvement
  advice based on a structured 5-check pipeline. Use when the user says "audit
  skill", "review skill", "check skill quality", "lint skill", "skill report",
  or provides a skill folder path for quality evaluation.
  CRITICAL ROUTING RULE: This skill ONLY analyzes existing skills for quality —
  it does NOT create new skills, run evals, or benchmark. For creating or
  iterating skills, use skill-creator:skill-creator instead.
  Input: a local skill folder path containing SKILL.md.
  Output: a structured quality report with PASS/WARN/FAIL per check and specific
  improvement suggestions, printed to the conversation. No files are created or
  modified — this is a read-only diagnostic tool.
---

# Skill Creator — Skill Quality Auditor

Analyze a skill's SKILL.md and supporting files against a structured quality pipeline, then present a diagnostic report with specific improvement suggestions. This skill is the automated version of a manual skill description audit.

## Language Behavior

Default to English. If the user writes in Chinese, respond in Chinese.

## Workflow

### Step 0: Validate Input Path

The user provides a skill folder path (relative or absolute). Validate:

1. **Path exists** and is a directory
2. **SKILL.md exists** inside the directory
3. **YAML frontmatter** is present (file starts with `---`)

If validation fails, STOP with a clear message:
- Missing directory: "Path does not exist: `{path}`. Provide a valid skill folder path."
- No SKILL.md: "No SKILL.md found in `{path}`. This does not appear to be a skill folder."
- No frontmatter: Note this as a finding (FAIL in Check 3) but continue the analysis.

### Step 1: Read Skill Content

Read and parse the target skill:

1. **SKILL.md** — split into:
   - Frontmatter fields (`name`, `description`, any others)
   - Body sections (split by `##` headings)
   - Total word count of description field
   - Total line count of the file
2. **Supporting directories** — list contents of `scripts/`, `references/`, `assets/` if they exist
3. **Plugin context** — identify the parent plugin by finding the nearest `plugin.json` up the directory tree

### Step 2: Run Analysis Pipeline

Run all 5 checks against the parsed content. Each check produces sub-check results with severity: **PASS**, **WARN**, or **FAIL**.

Severity guidelines:
- **FAIL**: Functional problem that will cause misrouting, broken invocations, or user confusion. Fix before deploying.
- **WARN**: Improvement opportunity that would increase quality but isn't blocking. Address when convenient.
- **PASS**: Meets or exceeds expectations. No action needed.

### Step 3: Compile and Present Report

1. Print the summary table (all 5 checks with status and key finding)
2. Print detailed findings for each check (sub-check table + specific suggestions)
3. Print a priority actions list (FAIL items first, then WARN)
4. **STOP** — do not chain into other skills, do not modify any files

## Analysis Pipeline

### Check 1: Description Quality

**Question: Is the frontmatter `description` sufficient for the model to correctly select this skill?**

| Sub-check | PASS | WARN | FAIL |
|-----------|------|------|------|
| **Existence** | `description` field present in frontmatter | — | No `description` field |
| **Length** | 50+ words | 20–49 words | <20 words |
| **Core purpose** | First sentence clearly states what the skill does | Purpose is vague or buried | No identifiable purpose statement |
| **Trigger phrases** | 3+ trigger phrases ("use when the user says...") | 1–2 trigger phrases | No trigger phrases |
| **Input format** | Explicitly states expected input and format | Input implied but not explicit | No input mentioned |
| **Output type** | Explicitly states what the skill produces | Output implied but not explicit | No output mentioned |
| **Negative guidance** | Includes "when NOT to use" or "do NOT use for" | — | No negative guidance AND similar skills exist |
| **Prerequisites** | Lists runtime requirements (CLIs, auth, files) | — | Has runtime deps but doesn't mention them |

### Check 2: Routing Clarity

**Question: Can the model reliably distinguish this skill from similar ones?**

To evaluate this check:
1. Scan all sibling skill directories (same plugin) — read their SKILL.md frontmatter
2. From the current session's system-reminder, extract the full skill list with descriptions
3. Compare the target skill against each discovered skill

| Sub-check | PASS | WARN | FAIL |
|-----------|------|------|------|
| **Name uniqueness** | No other skill shares the name | Name is a substring of another skill's name | Exact name collision with another skill |
| **Description disambiguation** | Description explicitly distinguishes from similar skills | Similar skills exist but no explicit disambiguation | High keyword overlap with another skill's description |
| **Routing rule** | CRITICAL ROUTING RULE present (if overlapping skills exist) | — | Overlapping skills exist but no routing rule |
| **Trigger phrase conflicts** | No shared trigger phrases with other skills | 1 shared trigger phrase | 3+ shared trigger phrases with another skill |

### Check 3: Structure Completeness

**Question: Does the SKILL.md follow skill authoring conventions?**

Adapt expectations based on the skill's plugin. For sentinel skills, check sentinel-specific patterns. For other plugins, check general best practices.

| Sub-check | PASS | WARN | FAIL |
|-----------|------|------|------|
| **YAML frontmatter** | Has `name` + `description` | Has `name` only | No frontmatter or malformed |
| **Overview section** | Present (first section after frontmatter) | — | Missing |
| **Workflow section** | Present with numbered steps | Present but steps unnumbered | Missing |
| **Step 0 (prerequisites)** | Present and validates input/state | — | Missing when skill has prerequisites or external deps |
| **Anti-patterns** | Present with "Do NOT / Do Instead" table | Present but not tabular | Missing (WARN) |
| **Language behavior** | Present (for user-facing skills) | — | Missing (WARN only for sentinel skills) |
| **Examples** | At least one usage example | — | No examples (WARN) |

### Check 4: Input/Output Contract

**Question: Are inputs, outputs, and edge cases clearly documented?**

| Sub-check | PASS | WARN | FAIL |
|-----------|------|------|------|
| **Input specification** | Clearly described with expected format | Mentioned but format unclear | Not specified |
| **Output specification** | Clearly described (files, stdout, artifacts) | Mentioned but vague | Not specified |
| **Edge cases** | At least 2 edge cases documented | 1 edge case documented | None documented (WARN) |
| **Error handling** | Describes behavior on failure/invalid input | — | No error guidance (WARN) |
| **Termination** | Clear statement of when the skill stops | — | Unclear whether skill chains or stops (WARN) |

### Check 5: System Prompt Interaction

**Question: Does the description behave well when loaded into a system prompt alongside many other skills?**

| Sub-check | PASS | WARN | FAIL |
|-----------|------|------|------|
| **Emphasis usage** | IMPORTANT/CRITICAL/NEVER used appropriately (1–3 instances) | Overuse (5+ emphasis keywords in description) | Emphasis needed but absent (e.g., critical routing distinction without CRITICAL) |
| **Keyword sensitivity** | No unintended keyword associations with other skills | Description contains generic words that match other skill names | — |
| **Description length** | 30–150 words in frontmatter description | 150–300 words | >300 words (system prompt bloat) or <30 words |
| **Instruction clarity** | Imperative, unambiguous instructions | Some passive or ambiguous phrasing | Contradictory instructions |

## Report Format

Present the report in this structure:

```
## Skill Quality Report: {skill-name}

**Plugin:** {plugin-name} | **Path:** {path} | **Date:** {YYYY-MM-DD}

### Summary

| # | Check | Status | Key Finding |
|---|-------|--------|-------------|
| 1 | Description Quality | {PASS/WARN/FAIL} | {one-line} |
| 2 | Routing Clarity | {PASS/WARN/FAIL} | {one-line} |
| 3 | Structure Completeness | {PASS/WARN/FAIL} | {one-line} |
| 4 | Input/Output Contract | {PASS/WARN/FAIL} | {one-line} |
| 5 | System Prompt Interaction | {PASS/WARN/FAIL} | {one-line} |

**Overall: {N} PASS, {N} WARN, {N} FAIL**

### Detailed Findings

#### Check 1: Description Quality

| Sub-check | Status | Detail |
|-----------|--------|--------|
| Existence | PASS | description field present ({N} words) |
| ... | ... | ... |

**Suggestions:**
- {specific, actionable improvement}
- {specific, actionable improvement}

#### Check 2–5: {same pattern}

### Priority Actions

1. **[FAIL]** {specific action item with what to change and why}
2. **[FAIL]** {specific action item}
3. **[WARN]** {specific action item}
```

The summary status for each check is the **worst** sub-check status: any FAIL sub-check makes the whole check FAIL; any WARN (with no FAIL) makes it WARN.

## Anti-Patterns

| Do NOT | Do Instead |
|--------|-----------|
| Modify the target SKILL.md | Only read and report; let the user decide what to fix |
| Apply fixes automatically | Present findings and suggestions; user or `skill-creator:skill-creator` handles changes |
| Fail silently on missing frontmatter | Report it as a FAIL finding with specific fix instructions |
| Only check sentinel conventions for non-sentinel skills | Adapt structure checks to the skill's plugin conventions |
| Report every minor style issue as FAIL | Use WARN for improvements; reserve FAIL for functional problems |
| Chain into skill-creator:skill-creator after reporting | STOP after presenting the report |
| Scan the entire filesystem for overlapping skills | Only scan sibling skills + system-reminder skill list |
| Produce a numeric quality score | Use categorized PASS/WARN/FAIL with specific findings |
| Skip the routing overlap check | Always run Check 2 — routing conflicts are the highest-impact quality issue |
| Write the report to a file | Print to conversation — this is advisory, not a project artifact |
