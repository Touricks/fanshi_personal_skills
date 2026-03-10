# Export — Compliance Lint + Format Rendering

## Overview

Produces submission-ready documents from project docs. Runs compliance lint (AI writing pattern detection) and renders output using user-provided templates.

Policy lives in `.sentinel/export/compliance.py`. This skill orchestrates only.

## Language Behavior

Default to English. If the user writes in Chinese, respond in Chinese. Match the user's language throughout.

## Workflow

### Step 0: Read Export Directory

List `docs/export/` contents:
- Templates (`.tex`, `.pptx`, `.docx`)
- Rubrics (`*rubric*`)
- `README.md`

If `docs/export/` doesn't exist, create it with `output/` subdirectory.

### Step 1: Identify Content Sources

Use AskUserQuestion: "Which documents do you want to export?"

Options:
- Specific files (e.g., `ARCHITECTURE.md`, `docs/sessions/2026-03-06.md`)
- "All project docs"
- Custom selection

### Step 2: Determine Output Format

Use AskUserQuestion: "What output format?"

- **Markdown** → proceed directly
- **PDF / PPTX / DOCX** → check `docs/export/` for matching template
  - Template found → confirm with user
  - **No template → STOP**: "No [format] template found in `docs/export/`. Please add one and re-run."

### Step 3: Run Compliance Lint

```bash
PYTHONPATH=.sentinel python -m export.compliance --input <file>
```

For multiple files, run on each and aggregate results.

### Step 4: Present Findings

Categorize by type, show counts:

```
## Compliance Report

| Type | Count | Auto-fixable |
|------|-------|--------------|
| Chain-of-thought (T1) | 3 | 0 |
| Structural tells (T2) | 7 | 4 |
| Phantom references (T3) | 1 | 0 |
| Statistical (T4) | - | - |

Total: 11 findings (4 auto-fixable, 7 need review)
```

Use AskUserQuestion with options:
1. "Apply auto-fixes (4 items) and review the rest"
2. "Show me all findings — I'll fix manually"
3. "Skip compliance"

### Step 5: Apply Fixes

If user chose auto-fix:
1. Apply auto-fixes via `apply_auto_fixes()`
2. Re-run compliance to get fresh offsets
3. Show delta: "Fixed 4 items. 7 findings remain for manual review."
4. List remaining findings with line numbers and suggestions

### Step 6: Rubric Check (optional)

If a rubric file exists in `docs/export/` (filename contains "rubric"):
- Parse rubric criteria
- Evaluate content against criteria
- Present score and gaps

If no rubric: skip silently.

### Step 7: Render Output

- **Markdown**: Write cleaned content to `docs/export/output/`
- **Non-markdown**: Invoke the appropriate document skill with the user's template
  - PDF: Use LaTeX template → compile
  - PPTX: Use `/pptx` skill with template
  - DOCX: Use `/docx` skill with template
- All output goes to `docs/export/output/`

### Step 8: Final Summary

```
## Export Complete

- Source: ARCHITECTURE.md
- Format: Markdown
- Compliance: 11 findings → 4 auto-fixed, 7 reviewed
- Output: docs/export/output/ARCHITECTURE-export.md
```

## Anti-Patterns

| Do NOT | Do Instead |
|--------|-----------|
| Generate random template for non-md | Ask user to provide template in `docs/export/` |
| Auto-fix Type 4 findings | Flag for human rewrite |
| Auto-fix borderline vocabulary (T2-D2) | Show suggestion, let user decide |
| Skip compliance without user consent | Always run; let user opt out at Step 4 |
| Overwrite source documents | Write to `docs/export/output/` only |
| Describe compliance patterns here | Reference `compliance.py` — policy in code |
| Scan inside code blocks or front matter | `compliance.py` handles segmentation |
| Run Type 4 without asking | Type 4 is opt-in; ask user if they want statistical analysis |
