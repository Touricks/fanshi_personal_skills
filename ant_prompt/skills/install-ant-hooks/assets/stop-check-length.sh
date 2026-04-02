#!/usr/bin/env bash
# Stop hook: soft-enforce response length limits.
#
# Advisory target: 100 words (set in SessionStart guidance).
# Hard ceiling: 200 words (blocks here). Tunable via HOOK_MAX_WORDS env var.
#
# Exit 0 = allow. Exit 2 = block (too long).
# Requires: jq

INPUT=$(cat)

STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
LAST_MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // empty')

# Guard: don't re-trigger after a block
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0
fi

if [ -z "$LAST_MSG" ]; then
  exit 0
fi

# Configurable threshold (default 200)
MAX_WORDS=${HOOK_MAX_WORDS:-200}

WORD_COUNT=$(echo "$LAST_MSG" | wc -w | tr -d ' ')

if [ "$WORD_COUNT" -gt "$MAX_WORDS" ]; then
  echo "Your final response is ${WORD_COUNT} words (limit: ${MAX_WORDS}). Please make it more concise: lead with the action, trim filler, and move process details to the end. The target is 100 words unless the task requires more detail." >&2
  exit 2
fi

exit 0
