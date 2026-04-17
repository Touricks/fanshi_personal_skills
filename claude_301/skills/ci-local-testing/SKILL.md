---
name: ci-local-testing
description: >
  Guide for locally testing Claude Code CI pipelines with structured JSON output.
  Assumes CLAUDE_CODE_OAUTH_TOKEN is already configured. Focuses on extracting
  structured_output from `--json-schema` results using jq, with precheck,
  output redirection, and CLAUDE.md context loading. Use when the user says
  "test CI locally", "claude -p", "structured output", "json-schema output",
  "extract CI results", "jq structured_output", "CI pipeline output", or wants
  to verify their CI JSON output configuration works before pushing to a real pipeline.
---

# CI Local Testing: Structured Output Extraction

Test your Claude Code CI pipeline locally. This skill assumes `CLAUDE_CODE_OAUTH_TOKEN` is already set in `.env` and focuses on getting machine-parseable structured output from `claude -p`.

---

## Precheck

Before running any tests, verify your token works:

```bash
source .env
CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" claude -p "say ok" --no-session-persistence
```

| Result | Meaning | Fix |
|--------|---------|-----|
| `ok` | Token valid | Proceed |
| `401 Invalid bearer token` | Token expired/revoked | Re-run `claude setup-token` |
| `ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN env var is required` | Env var not loaded | Check `.env` and `source` |

`setup-token` generates a 1-year `user:inference`-only OAuth token. The `inferenceOnly` scope covers everything `-p` mode needs — local tools (Grep, Bash, Read, etc.) execute in the Claude Code process, not through the API.

---

## Structured Output: The Core Pattern

```bash
CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" claude -p "<prompt>" --output-format json --json-schema '<schema>' --no-session-persistence
```

### How `--json-schema` works

Claude Code creates a synthetic `StructuredOutput` tool and instructs the model to call it with data matching your schema. AJV validates the output at runtime — if it doesn't conform, the model retries. The schema is **enforced**, not suggested.

### The output envelope

Every `--output-format json` response is wrapped in an envelope:

```json
{
  "type": "result",
  "subtype": "success",
  "result": "apples, bananas, oranges",
  "structured_output": {
    "fruits": ["apple", "banana", "orange"]
  },
  "total_cost_usd": 0.197,
  "duration_ms": 5615
}
```

**The critical distinction:** `result` is a plain-text summary. `structured_output` is the schema-validated data. CI scripts must extract from `structured_output`.

---

## Extracting Data with jq

### Basic extraction

```bash
# Full structured data
jq '.structured_output' output.json

# Specific field
jq '.structured_output.fruits' output.json

# Nested objects
jq '.structured_output.cities[].name' output.json
```

### Success/failure check

```bash
# Exit code 0 if success, non-zero if not
jq -e '.subtype == "success"' output.json > /dev/null

# Use in CI script
if jq -e '.subtype == "success"' output.json > /dev/null; then
  echo "OK"
else
  echo "FAIL"; exit 1
fi
```

### Format extracted data for downstream use

```bash
# One-line-per-item for shell loops
jq -r '.structured_output.findings[] | "\(.severity)\t\(.file):\(.line)\t\(.message)"' output.json

# Re-export as clean JSON (strip envelope)
jq '.structured_output' output.json > clean.json

# Count items
jq '.structured_output.findings | length' output.json
```

### Error field extraction

```bash
# Check what went wrong on failure
jq '.subtype' output.json          # "error_max_turns", "error_max_budget_usd", etc.
jq '.total_cost_usd' output.json   # How much was spent
jq '.duration_ms' output.json      # How long it took
```

---

## Local Test Examples

### Example 1: Simple array output

```bash
source .env && CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  claude -p "List 3 fruits" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"fruits":{"type":"array","items":{"type":"string"}}},"required":["fruits"]}' \
  --no-session-persistence \
  > /tmp/ci-test.json 2>/dev/null

jq '.structured_output.fruits' /tmp/ci-test.json
# ["apple", "banana", "orange"]
```

### Example 2: Object array with nested fields

```bash
source .env && CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  claude -p "Review this code for issues" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"findings":{"type":"array","items":{"type":"object","properties":{"file":{"type":"string"},"line":{"type":"number"},"severity":{"type":"string","enum":["error","warning","info"]},"message":{"type":"string"}},"required":["file","line","severity","message"]}}},"required":["findings"]}' \
  --max-turns 10 \
  --no-session-persistence \
  > /tmp/ci-review.json 2>/dev/null

# Extract each finding as a formatted line
jq -r '.structured_output.findings[] | "[\(.severity)] \(.file):\(.line) — \(.message)"' /tmp/ci-review.json
```

### Example 3: Redirect + success gate (CI pattern)

```bash
source .env && CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  claude -p "Summarize recent changes" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"summary":{"type":"string"},"risk_level":{"type":"string","enum":["low","medium","high"]}},"required":["summary","risk_level"]}' \
  --max-budget-usd 0.5 \
  --no-session-persistence \
  > /tmp/ci-summary.json 2>/tmp/ci-error.log

if jq -e '.subtype == "success"' /tmp/ci-summary.json > /dev/null 2>&1; then
  RISK=$(jq -r '.structured_output.risk_level' /tmp/ci-summary.json)
  echo "Risk: $RISK"
  [ "$RISK" = "high" ] && exit 1
else
  cat /tmp/ci-error.log; exit 1
fi
```

---

## Notes

**CLAUDE.md loads automatically** — `claude -p` reads CLAUDE.md from the CWD upward, identical to interactive mode. In CI, `actions/checkout` sets CWD to the repo root, so your project CLAUDE.md is picked up without extra configuration.

**Session isolation is automatic** — each `claude -p` invocation is a fresh session. No context leaks between separate invocations, which is why code generation and code review should be separate steps.

**Safety flags** — always set `--max-turns` and `--max-budget-usd` in CI to prevent runaway costs. Add `--no-session-persistence` since CI doesn't need session resume.
