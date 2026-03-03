---
name: push
description: |
  Stage, commit, and push all current changes to the remote with a human-readable
  summary and user approval before executing. Use when the user says "push",
  "push to github", "push all changes", "commit and push", "check status and push",
  "send this to remote", or "ship it". Does NOT create branches or pull requests —
  pushes to the current branch only.
allowed-tools:
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git branch:*)
  - Bash(git remote:*)
  - Bash(git rev-parse:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git push:*)
  - AskUserQuestion
---

# Push — Stage, Commit, and Push with Approval

## Process

### Phase 1: Collect Repository State

Run these commands in parallel to build a complete picture:

1. `git status` — working tree state (staged, unstaged, untracked)
2. `git diff HEAD --stat` — summary of all changes vs HEAD
3. `git diff HEAD` — full diff for internal analysis (do NOT dump to user)
4. `git log --oneline -5` — recent commits for message style matching
5. `git branch --show-current` — current branch name
6. `git rev-parse --abbrev-ref HEAD` — detect detached HEAD
7. `git remote -v` — verify remote exists

**Abort conditions — check before proceeding:**

| Condition | Detection | Action |
|-----------|-----------|--------|
| Nothing to commit | Clean working tree, no staged/unstaged/untracked | Tell user "Nothing to push — working tree is clean." Stop. |
| Detached HEAD | `rev-parse --abbrev-ref HEAD` returns literal "HEAD" | Tell user to create or checkout a branch first. Stop. |
| No remote | `git remote -v` returns empty | Tell user to add a remote. Stop. |
| No upstream | `rev-parse --abbrev-ref @{upstream}` fails | Note this; offer `push -u origin <branch>` in Phase 3. |

### Phase 2: Analyze Changes

Categorize every changed file:

- **New** — untracked files
- **Modified** — tracked files with changes
- **Deleted** — removed files
- **Renamed** — files detected as renames

Group by purpose when possible. If >15 files, summarize by directory instead of listing each file.

**Draft a commit message:**

- Match the style of the 5 recent commits (conventional commits, imperative mood, etc.)
- Explain WHAT changed and WHY, not just list files
- First line under 72 characters; add body if changes are complex

### Phase 3: Present Summary and Request Approval

Use `AskUserQuestion` to show the summary and get explicit approval. Format:

```
## Changes to push (branch: <branch>)

### Files
- [New] path/to/file
- [Modified] path/to/file
- [Deleted] path/to/file
- [Renamed] old/path -> new/path

### Summary
<1-3 sentence description of what changed>

### Proposed commit message
<the drafted message>
```

If no upstream, append: "No upstream set. Will push with `git push -u origin <branch>`."

**Wait for user response. Do NOT proceed without approval.**

Handle responses:
- Approve → proceed to Phase 4
- User provides alternative commit message → use theirs
- Cancel → stop, nothing pushed
- User excludes files → adjust staging accordingly

### Phase 4: Execute

Only after approval:

1. **Stage**: `git add` relevant files. If all approved: `git add -A`.
   If user excluded files: add only approved files by name.
   **NEVER stage .env, credentials.json, .secret, *.pem, *.key without explicit user confirmation.**
2. **Commit**: `git commit -m "<approved message>"` via heredoc for multi-line.
3. **Push**: `git push` (or `git push -u origin <branch>` if no upstream).

### Phase 5: Confirm

On success:
```
Pushed to origin/<branch>: <hash> <message>
(<N> files changed, <insertions> insertions, <deletions> deletions)
```

On failure — report clearly, never force-push:
- Rejected (non-fast-forward) → "Remote has new changes. Run `git pull` first."
- Permission denied → "Auth failed. Check credentials or SSH key."
- Remote not found → "Verify URL with `git remote -v`."

## Anti-Patterns

| Do Not | Do Instead |
|--------|-----------|
| Push without showing summary | Always present changes first |
| Auto-commit without approval | Wait for explicit approval |
| Force-push to resolve conflicts | Report error, let user decide |
| Stage secret files silently | Warn and require explicit confirmation |
| Create branches or PRs | Stay on current branch |
| Dump full diff to user | Summarize in natural language |
| Use generic messages like "update files" | Draft specific messages from actual changes |
