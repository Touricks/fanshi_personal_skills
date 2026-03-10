#!/bin/bash
# Validate .sentinel/tmp/loop-launch.md format and nonce consistency.
# New format: single copy-pasteable /ralph-loop:ralph-loop command.
# Usage: bash validate-launch.sh [path]
# Default path: .sentinel/tmp/loop-launch.md
# Exit 0 = pass, exit 1 = fail (with diagnostics)

set -euo pipefail

FILE="${1:-.sentinel/tmp/loop-launch.md}"
ERRORS=0

fail() { echo "FAIL: $1"; ERRORS=$((ERRORS + 1)); }
pass() { echo "  ok: $1"; }

echo "Validating: $FILE"
echo "---"

# 1. File exists
if [[ ! -f "$FILE" ]]; then
  fail "File does not exist: $FILE"
  exit 1
fi
pass "file exists"

CONTENT=$(cat "$FILE")

# 2. Starts with /ralph-loop:ralph-loop
if echo "$CONTENT" | head -1 | grep -q '^/ralph-loop:ralph-loop '; then
  pass "starts with /ralph-loop:ralph-loop"
else
  fail "file must start with '/ralph-loop:ralph-loop '"
fi

# 3. No triple backticks (breaks ralph-loop bash parser)
if echo "$CONTENT" | grep -q '```'; then
  fail "contains triple backticks — will break ralph-loop bash parser"
else
  pass "no triple backticks"
fi

# 4. Required sections in prompt body
for section in "Task Objective" "Completion Condition" "Boundaries"; do
  if echo "$CONTENT" | grep -q "## $section"; then
    pass "has '## $section' section"
  else
    fail "missing '## $section' section"
  fi
done

# 5. --completion-promise flag
CMD_NONCE=$(echo "$CONTENT" | grep -oE '\-\-completion-promise "[^"]+"' | head -1 | sed 's/--completion-promise "//;s/"$//')
if [[ -n "$CMD_NONCE" ]]; then
  pass "has --completion-promise flag: $CMD_NONCE"
else
  fail "no --completion-promise flag found"
fi

# 6. <promise> tag in prompt body
PROMPT_NONCE=$(echo "$CONTENT" | grep -oE '<promise>[^<]+</promise>' | head -1 | sed 's/<promise>//;s/<\/promise>//')
if [[ -n "$PROMPT_NONCE" ]]; then
  pass "has <promise> tag in prompt: $PROMPT_NONCE"
else
  fail "no <promise> tag found in prompt body"
fi

# 7. Nonce consistency
if [[ -n "$CMD_NONCE" ]] && [[ -n "$PROMPT_NONCE" ]]; then
  if [[ "$CMD_NONCE" = "$PROMPT_NONCE" ]]; then
    pass "nonces match"
  else
    fail "nonce mismatch: flag='$CMD_NONCE' vs prompt='$PROMPT_NONCE'"
  fi
fi

# 8. Nonce format (SENTINEL_ prefix with alphanumeric segments)
if [[ -n "$CMD_NONCE" ]]; then
  if echo "$CMD_NONCE" | grep -qE '^SENTINEL_[A-Z0-9]+_[A-Za-z0-9]{4,8}$'; then
    pass "nonce follows SENTINEL_ format"
  else
    fail "nonce '$CMD_NONCE' does not match SENTINEL_{ID}_{random} pattern"
  fi
fi

# 9. --max-iterations flag
if echo "$CONTENT" | grep -q '\-\-max-iterations'; then
  pass "has --max-iterations flag"
else
  fail "no --max-iterations flag found"
fi

# 10. Payload size check
SIZE=$(wc -c < "$FILE")
if [[ $SIZE -gt 51200 ]]; then
  fail "payload too large (${SIZE} bytes > 50KB) — may hit shell argv limits"
else
  pass "payload size ok (${SIZE} bytes)"
fi

# Summary
echo "---"
if [[ $ERRORS -eq 0 ]]; then
  echo "PASSED: all checks ok"
  exit 0
else
  echo "FAILED: $ERRORS error(s)"
  exit 1
fi
