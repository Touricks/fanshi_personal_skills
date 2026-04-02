#!/usr/bin/env bash
# PostToolUse hook for Edit and Write tools.
# Detects excessive new comment lines and injects a reminder.
# Advisory only (exit 0) -- never blocks.
#
# Requires: jq

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Extract the new/changed content depending on tool type
if [ "$TOOL_NAME" = "Edit" ]; then
  NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // empty')
elif [ "$TOOL_NAME" = "Write" ]; then
  NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')
else
  exit 0
fi

# No content to check
if [ -z "$NEW_CONTENT" ]; then
  exit 0
fi

# Count comment-like lines across common languages
# Matches: //, #, /*, *, --, <!--, """, '''
COMMENT_COUNT=$(echo "$NEW_CONTENT" | grep -cE '^\s*(//|#[^!]|/\*|\*[^/]|--|<!--|"""|'"'"''"'"''"'"')' 2>/dev/null || echo 0)

# Threshold: >3 comment lines triggers advisory (avoids noise from license headers)
if [ "$COMMENT_COUNT" -gt 3 ]; then
  cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Comment check: ${COMMENT_COUNT} comment-like lines detected in this edit. Reminder: default to writing no comments. Only add one when the WHY is non-obvious (hidden constraint, subtle invariant, workaround). Don't explain WHAT the code does or reference the current task/fix."
  }
}
ENDJSON
else
  exit 0
fi
