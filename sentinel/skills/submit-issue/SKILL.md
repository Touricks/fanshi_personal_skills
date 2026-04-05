---
name: submit-issue
description: Submit a bug report or feature request to the Sentinel-Coding GitHub repository. Use when the user says "submit issue", "report bug", "file issue", "report issue", "feature request", "found a bug", or wants to report a problem with Sentinel-Coding. Requires gh CLI installed and authenticated.
---

# Submit Issue

Submit a structured GitHub Issue (bug report or feature request) to the Sentinel-Coding repository directly from Claude Code, with automatic environment detection and template alignment.

## Language Behavior

Default to English. If the user writes in another language, match that language for all prompts and the generated issue body. The issue title prefix (`[Bug]` / `[Feature]`) stays in English regardless.

## Workflow

### Step 0: Check Prerequisites

Run the following commands silently:

```bash
gh --version
gh auth status
```

- If `gh` is not found: inform the user — "The `gh` CLI is required. Install with `brew install gh` (macOS), `sudo apt install gh` (Ubuntu), or visit https://cli.github.com/. Then run `gh auth login` to authenticate." **STOP.**
- If `gh` is installed but not authenticated: inform the user — "Run `gh auth login` to connect your GitHub account, then try again." **STOP.**

### Step 1: Determine Issue Type

Use AskUserQuestion with two options:

1. **Bug report** — something isn't working correctly
2. **Feature request** — suggest a new feature or improvement

If the user's initial message already clearly indicates one type (e.g., "I found a bug in /start"), infer the type and confirm rather than asking.

### Step 2: Auto-Gather Environment Context

Run these commands silently to collect environment info:

```bash
uname -s -r                          # OS kernel
sw_vers -productVersion 2>/dev/null  # macOS version (skip on Linux)
python3 --version                    # Python version
claude --version 2>/dev/null         # Claude Code version (may not exist)
```

Parse the Sentinel-Coding version from `CHANGELOG.md` — extract the version number from the first `## [x.y.z]` header.

Scan the current conversation context for any `/skill-name` invocations to detect which skill was active.

Present the gathered info to the user for confirmation:

> **Detected environment:**
> - OS: macOS 15.5 (Darwin 24.6.0)
> - Python: 3.11.5
> - Claude Code: 1.0.x
> - Sentinel-Coding: 0.1.0
> - Skill involved: /start (detected from conversation)
>
> Is this correct? Any corrections?

### Step 3: Gather User Description

#### Bug report path

Ask the user:
- **Describe the bug**: What went wrong?
- **Steps to reproduce**: Numbered steps to trigger the bug
- **Expected behavior**: What should have happened?
- **Actual behavior**: What actually happened?
- **Relevant logs / error output** (optional): Any error messages or stack traces?

Collect all in 1–2 rounds of AskUserQuestion. If the user's initial message already provides some of these, pre-fill and confirm.

#### Feature request path

Ask the user:
- **Problem / Use Case**: What problem does this feature solve?
- **Proposed Solution**: Describe your proposed approach
- **Alternatives Considered** (optional): Any other approaches?
- **Context**: Which skill or component would this affect?

### Step 4: Compose Issue Body

Format the issue body to **exactly match** the corresponding GitHub issue template.

#### Bug report body

```markdown
## Describe the Bug

{user's description}

## Environment

- OS: {auto-detected}
- Python version: {auto-detected}
- Claude Code version: {auto-detected or "unknown"}
- Sentinel-Coding version: {parsed from CHANGELOG}

## Steps to Reproduce

{user's numbered steps}

## Expected Behavior

{user's expected behavior}

## Actual Behavior

{user's actual behavior}

## Relevant Logs / Error Output

{user's logs or "N/A"}

## Skill Involved

Which skill was active when the bug occurred?

- [{x if detected}] /start
- [{x if detected}] /routing
- [{x if detected}] /boundary
- [{x if detected}] /sentinel-loop
- [{x if detected}] /progress
- [{x if detected}] /sentinel-export
- [{x if detected}] /call-codex
- [{x if detected}] /submit-issue
- [ ] Hooks / chain-triggers
- [ ] Other
```

#### Feature request body

```markdown
## Problem / Use Case

{user's problem description}

## Proposed Solution

{user's proposed solution}

## Alternatives Considered

{user's alternatives or "N/A"}

## Context

- Which skill or component would this affect? {detected or user-specified}
- Is this a new skill, template extension, or compliance rule? {inferred}
```

#### Title generation

- Bugs: `[Bug] {concise summary, max 70 chars}`
- Features: `[Feature] {concise summary, max 70 chars}`

#### Privacy scan

Before presenting the preview, scan the composed body for:
- Local file paths containing usernames (e.g., `/Users/john/...`) — replace with `~/...`
- Tokens or secrets (patterns like `sk-...`, `ghp_...`, `Bearer ...`, API keys)
- Internal hostnames or private IPs

If found, warn the user and offer to redact before submission.

### Step 5: Duplicate Detection and Preview

#### Duplicate check

Search for similar existing issues:

```bash
gh issue list --repo Touricks/Sentinel_coding_sdk --search "{keywords from title}" --state open --limit 5
```

If similar issues are found, present them:

> **Potentially related open issues:**
> - #12: [Bug] Compaction fails on empty YAML
> - #8: [Bug] progress.yaml parser error
>
> Options:
> 1. **Submit anyway** — this is a different issue
> 2. **Comment on existing issue** — add context to one of these
> 3. **Cancel**

If the user chooses "comment on existing," use `gh issue comment {number} --repo Touricks/Sentinel_coding_sdk --body "..."` instead.

#### Preview

Display the complete issue:

> **Issue Preview**
>
> **Title:** [Bug] /start fails when PRD.md already exists
> **Labels:** bug
>
> **Body:**
> *(full formatted body)*

Use AskUserQuestion with options:
1. **Submit to GitHub**
2. **Edit first** — describe what to change
3. **Cancel**

If the user chooses "Edit first," accept modifications and re-preview. Maximum 3 edit rounds, then offer the formatted body for manual copy-paste.

### Step 6: Submit

```bash
gh issue create \
  --repo Touricks/Sentinel_coding_sdk \
  --title "[Bug] concise summary here" \
  --body "$(cat <<'ISSUE_BODY'
{formatted body}
ISSUE_BODY
)" \
  --label "bug"
```

For feature requests, use `--label "enhancement"` instead of `--label "bug"`.

**On success:** Extract and display the issue URL from `gh` output.

> Issue submitted successfully: https://github.com/Touricks/Sentinel_coding_sdk/issues/42

**On failure:** Display the error and provide the formatted body for manual submission:

> Submission failed: {error message}
>
> You can submit manually at https://github.com/Touricks/Sentinel_coding_sdk/issues/new
>
> Here is the formatted body to copy:
> *(full body)*

## Important Notes

- Use single-quoted heredoc delimiter (`'ISSUE_BODY'`) to prevent shell expansion of backticks and `$variables` in the issue body.
- The target repository defaults to `Touricks/Sentinel_coding_sdk`. If the user specifies a different repo, use that instead.
- If `gh` returns a rate-limit error, show the error and provide the body for manual submission.

## Anti-Patterns

| Do NOT | Do Instead |
|--------|-----------|
| Auto-submit without user preview | Always show full preview and get explicit confirmation |
| Fabricate reproduction steps or details | Only include content the user provided |
| Include sensitive information (file paths with usernames, tokens, API keys) | Scan for common patterns and warn before submission |
| Continue if `gh` is not installed or authenticated | STOP with clear installation / authentication instructions |
| Generate a title longer than 70 characters | Keep title concise; put details in the body |
| Skip duplicate detection | Search existing issues before submitting |
| Dump the entire conversation as context | Only include relevant, user-approved content |
| Submit to a fork or wrong repo | Default to `Touricks/Sentinel_coding_sdk` |
| Retry on failure without telling the user | Show the error and offer manual fallback |
