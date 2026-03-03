---
name: prompt-architect
description: "Transform vague user requirements into structured, high-quality prompts. Uses an 8-module framework (persona, objective, data grounding, writing style, visual design, module structure, technical rules, quality bar) to diagnose gaps and iteratively fill them. Triggers when the user says \"help me write a prompt\", \"optimize this prompt\", \"formalize my requirement\", \"design a prompt\", or \"this prompt isn't good enough\"."
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

# Prompt Architect -- 8-Module Prompt Structuring Tool

## Overview

Uses an 8-module framework to progressively transform a vague user requirement into a complete, ready-to-use, structured prompt. The framework is derived from reverse-engineering top-tier prompts (see `references/criteria.md` for full definitions and examples).

## Language Behavior

Default to English. If the user writes in Chinese, respond in Chinese. Match the user's language throughout the session.

## When to Use

- User has a vague requirement and wants help writing or optimizing a prompt
- User says "help me design a prompt", "this prompt isn't good enough", "structure my requirement"
- User says "formalize my requirement", "design a prompt", "optimize this prompt"
- User has a rough prompt draft and wants systematic improvement

## 8-Module Framework Reference

| # | Module | Core Question |
|---|--------|---------------|
| 1 | Persona and Audience | Who does the AI play? Who is the reader? |
| 2 | Core Objective and Deliverable | What to do? What output format? |
| 3 | Data Grounding and External Inputs | Where does data come from? How to prevent hallucination? |
| 4 | Information Density and Writing Style | How concise? What tone? What is forbidden? |
| 5 | Visual and Design System | Color scheme? Typography? Layout rules? |
| 6 | Modular Micro-Structure | What goes in each section/sheet? |
| 7 | Medium-Specific Technical Rules | Low-level constraints of the output medium? |
| 8 | Top-Tier Quality Bar | What real-world standard to benchmark against? |

For detailed definitions and examples, load `references/criteria.md` with the Read tool when needed.

## Process

### Phase 1: Intake and Quick Diagnosis

Upon receiving the user's requirement, immediately perform an 8-module mapping analysis.

**Steps:**

1. Read the user's raw requirement carefully (could be a single sentence, a paragraph, or a rough prompt)
2. Evaluate coverage against each of the 8 modules
3. Output a diagnostic table:

```
## Diagnostic Results

| # | Module | Status | Findings |
|---|--------|--------|----------|
| 1 | Persona and Audience | Covered | "Senior data analyst" |
| 2 | Core Objective | Partial | Goal is clear but delivery format unspecified |
| 3 | Data Grounding | Missing | No data source mentioned |
| ... | ... | ... | ... |
```

**Status criteria:**

- Covered: User has provided sufficiently specific information
- Partial: Mentioned but not specific enough, or only half of the module is addressed
- Missing: Not mentioned at all

### Phase 2: Applicability Assessment

Not every module applies to every task. Assess applicability immediately after diagnosis.

**Common N/A scenarios:**

| Task Type | Typically N/A Modules |
|-----------|----------------------|
| Plain text conversation/Q&A | 5-Visual Design, 7-Technical Rules |
| Code generation | 5-Visual Design (unless generating UI code) |
| Simple translation/rewriting | 5-Visual Design, 6-Module Structure, 7-Technical Rules |
| Data analysis scripts | 5-Visual Design (unless chart styling is needed) |

**Steps:**

1. Mark non-applicable modules as `N/A` in the diagnostic table with a brief reason
2. Use AskUserQuestion to confirm with the user:
   - Whether your applicability assessment is correct
   - Whether they have additional information to add

Example question:

```
I've assessed these modules as not applicable to your task:
- Module 5 (Visual Design): Your task produces plain text output
- Module 7 (Technical Rules): No specific medium constraints
Is this assessment correct? Also, I noticed the following key gaps in your requirement...
```

### Phase 3: Module-by-Module Completion

For each applicable module with status "Missing" or "Partial", use AskUserQuestion to interactively fill the gaps.

**Question priority** (highest to lowest):

1. **Module 2 -- Core Objective and Deliverable** (nothing works without a clear goal)
2. **Module 1 -- Persona and Audience** (determines terminology and tone)
3. **Module 3 -- Data Grounding** (key to preventing hallucination)
4. **Module 4 -- Information Density and Writing Style** (directly affects perceived output quality)
5. **Module 6 -- Modular Micro-Structure** (section planning)
6. **Module 8 -- Top-Tier Quality Bar** (benchmark setting)
7. **Module 5 -- Visual and Design System** (if applicable)
8. **Module 7 -- Medium-Specific Technical Rules** (if applicable)

**Questioning strategy:**

- Maximum 4 questions per AskUserQuestion round (tool limit)
- Each question provides 2-4 options plus a custom option
- Options should reflect common best practices for that module (reference `references/criteria.md` examples)
- If user selects custom, follow up for details

**Typical question templates per module:**

**Module 1 -- Persona and Audience:**
- "What role should the AI play?" -- Options: Domain expert / Assistant / Teacher / Analyst
- "Who is the target audience?" -- Options: Professionals / General users / Decision-makers

**Module 2 -- Core Objective:**
- "What format should the final deliverable be?" -- Options: Code file / Document (PDF/Word) / Spreadsheet (Excel) / Plain text
- "Describe the task goal in one sentence" -- Open-ended

**Module 3 -- Data Grounding:**
- "Where should the AI get its facts?" -- Options: User-uploaded files / Web search / Specified database / AI's own knowledge (allowed)
- "Hallucination tolerance?" -- Options: Zero tolerance (must cite source) / Low tolerance (flag uncertain parts) / Speculation acceptable

**Module 4 -- Writing Style:**
- "Information density preference?" -- Options: Ultra-concise (bullet points) / Moderate (short paragraphs) / Detailed (long-form)
- "Tone preference?" -- Options: Formal professional / Friendly approachable / Academic objective

**Module 5 -- Visual (if applicable):**
- "Any color scheme or brand preference?" -- Options: Investment bank style (navy + gold) / Tech style (black + blue) / Clean white
- "Font preference?" -- Options: Sans-serif (Calibri/Arial) / Serif (Times) / Monospace (Consolas) / No preference

**Module 6 -- Structure:**
- Based on the confirmed core objective, propose a section outline for user confirmation or adjustment

**Module 7 -- Technical Rules (if applicable):**
- Based on delivery format, propose technical constraints (e.g., Excel auto-fit columns, PDF no mid-sentence breaks)

**Module 8 -- Quality Bar:**
- "What is your quality benchmark?" -- Options: Top-tier consulting firm report / Academic paper standard / Production-grade code
- "Should the AI output be usable without manual editing?" -- Yes / Minor edits acceptable

**Iteration rules:**
- After each round, update the diagnostic table statuses
- If all applicable modules reach "Covered", proceed to Phase 4
- If gaps remain, continue to the next round of questions

### Phase 4: Output Structured Prompt

Once all applicable modules are filled, generate the final structured prompt.

**Steps:**

1. Assemble collected information into a structured prompt
2. Display the complete prompt in the conversation
3. Use the Write tool to save as a .md file (filename format: `prompt-[task-keyword].md`, written to the user's current working directory)

**Output template:**

```markdown
# [Task Title]

## 1. Persona and Audience
- **AI Role**: [Specific identity, professional background, capability scope]
- **Target Audience**: [Reader/user profile, expertise level, expectations]

## 2. Core Objective and Deliverable
- **Task Goal**: [One-sentence precise definition]
- **Delivery Format**: [File type / document format / programming language]
- **Success Criteria**: [What counts as "done"]

## 3. Data Grounding and External Inputs
- **Data Sources**: [Bound files / APIs / databases / search]
- **Factual Constraints**: [Hallucination prevention rules]
- **Citation Requirements**: [Whether sources must be annotated]

## 4. Information Density and Writing Style
- **Density Requirements**: [Word/line limits, data-over-prose priority]
- **Tone**: [Professional / approachable / academic / ...]
- **Forbidden**: [Specific banned expressions or vocabulary]

## 5. Visual and Design System
[If applicable]
- **Color Scheme**: [Primary + accent colors]
- **Typography**: [Font type and size]
- **Layout**: [Spacing, alignment, prohibitions]

[If not applicable] N/A -- [Reason]

## 6. Modular Micro-Structure
- **Overall Structure**: [Section / sheet / page breakdown]
- **Per-Module Content**:
  - [Module 1]: [Specific contents]
  - [Module 2]: [Specific contents]
  - ...

## 7. Medium-Specific Technical Rules
[If applicable]
- **Output Medium**: [Excel / PDF / HTML / ...]
- **Technical Constraints**: [Specific formatting / rendering / compatibility requirements]

[If not applicable] N/A -- [Reason]

## 8. Top-Tier Quality Bar
- **Benchmark**: [Real-world quality reference]
- **Acceptance Criteria**: [Specific pass/fail conditions]
```

**After writing the file, inform the user of the file path.**

## Anti-Patterns

| Do Not | Do Instead |
|--------|-----------|
| Ask all questions for all 8 modules at once | Ask progressively in rounds, ordered by priority |
| Force questions on obviously inapplicable modules | Assess N/A intelligently and confirm with the user |
| Skip a module when the user says "whatever" | Suggest a reasonable default and ask for confirmation |
| Omit user-provided information from the output | Cross-check every user input is included in the final prompt |
| Use vague wording in the prompt ("as good as possible", "appropriate length") | All requirements must be specific and quantifiable |
| Generate the prompt without showing a diagnostic comparison | Before final output, briefly recap: what was missing and what was filled |

## Edge Cases

**User's input is already a high-quality prompt:**
Still run the 8-module diagnosis. If most modules are "Covered", tell the user their prompt is already comprehensive. Only suggest improvements for the few "Partial" or "Missing" modules. Do not force the full workflow.

**User says "help me optimize" but provides no original prompt:**
Ask first: "Please provide the prompt or requirement description you want to optimize. This can be a one-line summary or a full existing prompt."

**User says "I'm not sure" or "you decide" for a module:**
Provide a recommended default based on the task type. Clearly label it as a suggested value that the user can change anytime.

**Requirement involves multiple independent tasks:**
Suggest splitting them, running the 8-module process for each task separately. If the tasks are highly related, cover them in a single prompt but clearly delineate them in the "Modular Micro-Structure" section.
