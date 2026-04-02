---
name: remove-ant-hooks
description: Remove Anthropic coding standard hooks from the current project. Cleans hook entries from .claude/settings.json and optionally deletes copied scripts. Use when the user says "remove ant hooks", "uninstall ant mode", "disable coding hooks", "remove ant prompt", or "uninstall hooks".
---

# Remove Ant-Mode Hooks

Cleanly removes ant-mode hook entries from `.claude/settings.json` and optionally deletes the copied hook scripts from `.claude/hooks/`.

## Procedure

### Phase 1: Check Current State

1. Read `.claude/settings.json`
2. If file does not exist or has no `hooks` key: report "No ant-mode hooks are installed in this project" and stop
3. Search all hook entries for commands containing any of these filenames:
   - `session-start-guidance.sh`
   - `post-edit-comments.sh`
   - `stop-verify-completion.sh`
   - `stop-check-length.sh`
4. If none found: report "No ant-mode hooks found in settings" and stop
5. List the found entries and confirm removal with the user

### Phase 2: Remove Hook Entries

For each event key (`SessionStart`, `PostToolUse`, `Stop`) in the `hooks` object:

1. Filter out hook group entries that contain commands referencing any of the 4 ant-prompt script filenames
2. If an event's array becomes empty after filtering, remove the event key entirely
3. If the entire `hooks` object becomes empty, remove the `hooks` key
4. Use `jq` for all JSON manipulation to ensure valid output

Example `jq` approach:
```bash
jq '
  .hooks.SessionStart |= map(select(.hooks | all(.command | test("session-start-guidance\\.sh") | not))) |
  .hooks.PostToolUse |= map(select(.hooks | all(.command | test("post-edit-comments\\.sh") | not))) |
  .hooks.Stop |= map(select(.hooks | all(.command | test("stop-(verify-completion|check-length)\\.sh") | not))) |
  .hooks |= with_entries(select(.value | length > 0)) |
  if .hooks == {} then del(.hooks) else . end
' .claude/settings.json > /tmp/cleaned-settings.json
mv /tmp/cleaned-settings.json .claude/settings.json
```

### Phase 3: Clean Up Scripts

1. Use AskUserQuestion: "Also delete the hook scripts from `.claude/hooks/`?"
2. If yes, remove only the ant-prompt scripts:
   ```
   rm -f .claude/hooks/session-start-guidance.sh
   rm -f .claude/hooks/post-edit-comments.sh
   rm -f .claude/hooks/stop-verify-completion.sh
   rm -f .claude/hooks/stop-check-length.sh
   ```
3. If `.claude/hooks/` is now empty, remove the directory: `rmdir .claude/hooks 2>/dev/null`

### Phase 4: Verify & Report

1. Run `jq . .claude/settings.json` to confirm valid JSON
2. Report what was removed:
   - Which hook entries were removed from settings.json
   - Whether scripts were deleted
3. Note: "Restart your Claude Code session for changes to take effect"

## Anti-Patterns

| Do Not | Do Instead |
|--------|-----------|
| Delete all hooks indiscriminately | Only remove entries matching ant-prompt script names |
| Delete `.claude/settings.json` entirely | Surgically remove hook entries, preserve other settings |
| Remove hooks from global settings | Only operate on project-scoped `.claude/settings.json` |
| Skip JSON validation after editing | Always verify with `jq .` |
