---
name: install-ant-hooks
description: Install Anthropic-internal coding standard hooks into the current project. Copies hook scripts to .claude/hooks/ and merges configuration into .claude/settings.json. Use when the user says "install ant hooks", "add ant mode", "enable coding standards", "install coding hooks", "enhance hooks", or "set up ant prompt".
---

# Install Ant-Mode Hooks

Installs 4 hook scripts that replicate 7 Anthropic-internal (`USER_TYPE=ant`) coding standards into the current project as project-scoped Claude Code hooks.

## Procedure

### Phase 1: Locate Source Assets

The hook scripts are bundled as assets alongside this SKILL.md.

1. Find the `assets/` directory relative to this skill — use Glob for `**/install-ant-hooks/assets/session-start-guidance.sh`
2. Store the directory as `ASSETS_DIR`
3. Verify all 5 files exist in `ASSETS_DIR`:
   - `session-start-guidance.sh`
   - `post-edit-comments.sh`
   - `stop-verify-completion.sh`
   - `stop-check-length.sh`
   - `settings.json`

### Phase 2: Check Prerequisites

1. Run `which jq` — if missing, tell the user:
   - macOS: `brew install jq`
   - Ubuntu/Debian: `sudo apt-get install jq`
   - Stop and wait for the user to install it
2. Run `mkdir -p .claude/hooks` in the target project root

### Phase 3: Detect Existing Installation

1. If `.claude/settings.json` exists, read it
2. Search for `session-start-guidance.sh` in any hook command entries
3. If found: report "Ant-mode hooks are already installed" and use AskUserQuestion to ask whether to reinstall/update or cancel
4. If not found: proceed

### Phase 4: Copy Scripts

1. Copy all 4 `.sh` files from `ASSETS_DIR` to `.claude/hooks/`:
   ```
   cp ASSETS_DIR/session-start-guidance.sh .claude/hooks/
   cp ASSETS_DIR/post-edit-comments.sh .claude/hooks/
   cp ASSETS_DIR/stop-verify-completion.sh .claude/hooks/
   cp ASSETS_DIR/stop-check-length.sh .claude/hooks/
   ```
2. Make them executable: `chmod +x .claude/hooks/*.sh`

### Phase 5: Build & Merge Hook Config

1. Read `ASSETS_DIR/settings.json` (the template)
2. Resolve `HOOKS_DIR` to the absolute path of `.claude/hooks` in the current project:
   ```
   HOOKS_DIR="$(cd .claude/hooks && pwd)"
   ```
3. Replace all `$HOOKS_DIR` occurrences in the template with the resolved absolute path
4. This produces the resolved hooks JSON block

**Merge strategy** — handle 3 scenarios:

**A. No `.claude/settings.json` exists:**
- Write the resolved hooks JSON as the entire file

**B. File exists but has no `hooks` key:**
- Use `jq` to add the `hooks` key from the resolved template:
  ```
  jq -s '.[0] * .[1]' .claude/settings.json /tmp/ant-hooks-resolved.json > /tmp/merged.json
  mv /tmp/merged.json .claude/settings.json
  ```

**C. File exists with existing `hooks` key:**
- For each event (`SessionStart`, `PostToolUse`, `Stop`):
  - If the event does not exist in current settings, add it with the new entries
  - If the event exists, append the new hook group entries to the existing array
  - Check for duplicates by comparing `command` paths — skip if already present
- Use `jq` for all JSON operations

### Phase 6: Verify & Report

1. Run `jq . .claude/settings.json` to confirm valid JSON
2. Verify all 4 scripts exist and are executable at the target paths
3. Report what was installed:

```
Ant-mode hooks installed successfully.

| Event | Hook | Behavior |
|-------|------|----------|
| SessionStart | session-start-guidance.sh | Advisory: injects 6 coding standards |
| PostToolUse (Edit) | post-edit-comments.sh | Advisory: reminds if >3 comment lines |
| PostToolUse (Write) | post-edit-comments.sh | Advisory: reminds if >3 comment lines |
| Stop | stop-verify-completion.sh | Enforcing: blocks unverified completion claims |
| Stop | stop-check-length.sh | Soft-enforce: blocks if >200 words |

Restart your Claude Code session for hooks to take effect.
```

## The 7 Coding Standards

1. **Comment Discipline** — No comments by default; only WHY, never WHAT
2. **Assertiveness** — Speak up about misconceptions and adjacent bugs
3. **Completion Verification** — Verify before claiming done
4. **Faithful Reporting** — Never misrepresent test results
5. **Communication Style** — Flowing prose, inverted pyramid, match expertise
6. **Length Limits** — 25 words between tools, 100 words final response
7. **Commit & PR Hygiene** — Never include model codenames, version numbers, "Claude Code", or Co-Authored-By lines in commits/PRs

## Customization

After installation, users can tune behavior:

- **Word count threshold**: `export HOOK_MAX_WORDS=150` (default: 200)
- **Comment threshold**: Edit `.claude/hooks/post-edit-comments.sh` line 31, change `-gt 3`
- **Disable enforcement**: In `stop-verify-completion.sh`, change `exit 2` to `exit 0`
- **Disable individual hooks**: Remove the entry from `.claude/settings.json`

## Anti-Patterns

| Do Not | Do Instead |
|--------|-----------|
| Install to global `~/.claude/settings.json` | Always use project-scoped `.claude/settings.json` |
| Overwrite existing hooks in settings.json | Merge/append new entries alongside existing ones |
| Modify the hook scripts during installation | Copy as-is; user customizes after install |
| Skip the verification step | Always run `jq .` and check file permissions |
