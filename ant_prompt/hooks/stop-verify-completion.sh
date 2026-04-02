#!/usr/bin/env bash
# Stop hook: enforce completion verification and faithful reporting.
#
# Check A: If model claims "done/complete" but no test/run evidence in transcript -> block
# Check B: If model claims "all tests pass" but transcript has failure indicators -> block
#
# Exit 0 = allow stop. Exit 2 = block and feed stderr to model.
# Requires: jq

INPUT=$(cat)

STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
LAST_MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // empty')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')

# Guard: prevent infinite loop (stop_hook_active=true means we already blocked once)
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0
fi

# Nothing to check
if [ -z "$LAST_MSG" ]; then
  exit 0
fi

# --- Check A: Completion claims without verification ---
CLAIMS_COMPLETE=false
echo "$LAST_MSG" | grep -qiE \
  '(task (is )?(now )?complete|all (changes|updates) (have been |are )?made|implementation (is )?done|finished implementing|ready for review|changes are in place)' \
  && CLAIMS_COMPLETE=true

if [ "$CLAIMS_COMPLETE" = "true" ] && [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  # Look for recent verification evidence in last 200 lines of transcript
  VERIFIED=false
  tail -200 "$TRANSCRIPT" | grep -qiE \
    '(npm test|npx jest|npx vitest|pytest|cargo test|go test|make test|bun test|jest |vitest |mocha |rspec|phpunit|\.\/[a-z].*\.(sh|py|js|ts)|node .*\.(js|ts)|python .*\.py|ruby .*\.rb)' \
    && VERIFIED=true

  if [ "$VERIFIED" = "false" ]; then
    echo "You claimed the task is complete, but there is no evidence of verification (test run, script execution, or output check) in the recent transcript. Before reporting completion, please run the relevant test or check the output. If you cannot verify, say so explicitly rather than claiming success." >&2
    exit 2
  fi
fi

# --- Check B: False test-pass claims ---
CLAIMS_PASS=false
echo "$LAST_MSG" | grep -qiE \
  '(all tests pass|tests (are |all )?pass(ing|ed)?|test suite pass|no (test )?failures|checks (all )?pass|lint(ing)? pass)' \
  && CLAIMS_PASS=true

if [ "$CLAIMS_PASS" = "true" ] && [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  HAS_FAILURES=false
  tail -300 "$TRANSCRIPT" | grep -qiE \
    '( FAIL|FAILED|FAILURE|Error:|AssertionError|AssertError|panic:|ERRORS|test(s)? failed|failures:|errors found|exit code [1-9]|✗|✘)' \
    && HAS_FAILURES=true

  if [ "$HAS_FAILURES" = "true" ]; then
    echo "Your response claims tests pass, but the transcript contains failure indicators. Report outcomes faithfully: if tests fail, say so with the relevant output. Never claim 'all tests pass' when output shows failures, and never suppress or simplify failing checks." >&2
    exit 2
  fi
fi

# All checks passed
exit 0
