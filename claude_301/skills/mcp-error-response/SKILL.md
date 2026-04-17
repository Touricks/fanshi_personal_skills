---
name: mcp-error-response
description: >
  Guide for designing structured error responses in MCP tools. Covers error
  classification (transient, validation, business, permission), the isError
  flag in MCP protocol and Anthropic API, retryable vs non-retryable errors,
  the critical distinction between access failures and valid empty results,
  structured error metadata design, and subagent error propagation patterns.
  Use when the user says "MCP error handling", "error response design",
  "isError flag", "tool error classification", "retryable errors", "error
  propagation", "tool returns wrong error", "empty result vs error", "when
  to retry MCP tool", "subagent error handling", "structured error response",
  "access failure vs empty result", or wants to design how MCP tools should
  report and classify errors for LLM agents.
  For tool description design, see mcp-tool-design instead.
  For platform-level MCP optimization, see mcp-tool-enhancement instead.
---

# MCP Error Response Design: Classification, Flags, and Propagation

Design error responses that let LLM agents make correct retry, correction, and escalation decisions. This skill covers how MCP tools should **report errors** — classifying them, setting the right flags, structuring metadata, and propagating failures through multi-agent chains. It sits between `mcp-tool-design` (which covers tool descriptions and schemas) and `mcp-tool-enhancement` (which covers platform-level discoverability). A perfectly designed tool with perfect discoverability still fails if it reports errors in ways the agent cannot interpret.

---

## Part 1: Error Classification

### 1.1 The Four Error Categories

Not all errors are equal. Different error types demand different agent responses. Classify every error your MCP tool can produce into one of these four categories:

| Category | Examples | Retryable? | Agent Action |
|----------|----------|------------|--------------|
| **Transient** | Network timeout, HTTP 429/529, service temporarily unavailable, connection reset | Yes | Retry with backoff |
| **Validation** | Bad input format, missing required field, type mismatch, value out of range | No (but correctable) | Read error details, fix input, re-call |
| **Business** | Insufficient balance, policy violation, quota exceeded, refund exceeds purchase | No | Report to user verbatim |
| **Permission** | Unauthorized (401), token expired, role mismatch, account suspended | No | Report to user; may prompt re-authentication |

The key insight: only **transient** errors should trigger automatic retry. Validation errors need input correction (a different operation than retry). Business and permission errors need human intervention.

### 1.2 Why Classification Matters for Agents

An unclassified `"Error: something went wrong"` forces the agent into one of two bad outcomes:

- **Blind retry** — wastes tokens and time on non-retryable errors, may trigger rate limits
- **Premature abandonment** — gives up on a retryable transient error that would have resolved in seconds

Claude Code's `classifyToolError()` already categorizes errors into telemetry-safe strings (TelemetrySafeError messages, errno codes like ENOENT/EACCES, named error types, or a generic fallback). Your MCP tool should classify errors at the source with even more precision — the server knows context the client cannot infer.

### 1.3 Classify at the Source

The MCP server — not the client — should classify errors. The server knows whether an HTTP 500 from an upstream API was a transient timeout (retryable) or a permanent schema violation (not retryable). The client only sees "500" and must guess.

**Bad — classification left to the client:**
```json
{
  "isError": true,
  "content": [{"type": "text", "text": "Internal server error"}]
}
```

**Good — classification done by the server:**
```json
{
  "isError": true,
  "content": [{"type": "text", "text": "{\"errorCategory\": \"transient\", \"isRetryable\": true, \"description\": \"Upstream API timed out after 30s. The service is healthy but slow under current load.\", \"retryAfterSeconds\": 5}"}]
}
```

---

## Part 2: The `isError` Flag

### 2.1 Two Protocols, Two Flag Names

The error signal travels through two protocol layers, each with its own flag:

| Layer | Flag | Where It Lives |
|-------|------|----------------|
| MCP Protocol | `isError: true` | On the `CallToolResult` object returned by the MCP server |
| Anthropic API | `is_error: true` | On the `ToolResultBlockParam` content block sent to the model |

Claude Code bridges these layers: when it receives `isError: true` from an MCP server, it throws a `McpToolCallError`, which gets caught and converted into a `tool_result` block with `is_error: true` for the model.

### 2.2 When to Set `isError: true`

Set the flag when the tool **could not perform its intended action**:

- Database connection failed
- API returned an authentication error
- Input validation failed (parameter missing or malformed)
- Business rule rejected the operation
- External service returned a 5xx error

### 2.3 When to Keep `isError: false`

Keep the flag false (or omit it) when the tool **succeeded**, even if the result is empty or negative:

- Query executed successfully but returned 0 rows
- Search completed but found no matches
- Deletion succeeded (nothing to return)
- Check passed — the condition is met (or not met, but the check itself worked)

The tool's job was to perform an operation. If it performed it, that's success — regardless of what the data says.

### 2.4 Code Example: Database Query

**Bad — treats empty results as an error:**
```typescript
// DON'T DO THIS
server.tool("query_users", { filter: z.string() }, async ({ filter }) => {
  const users = await db.query("SELECT * FROM users WHERE name LIKE ?", [filter]);
  if (users.length === 0) {
    return {
      isError: true,  // WRONG: query succeeded, just no matches
      content: [{ type: "text", text: "No users found" }]
    };
  }
  return { content: [{ type: "text", text: JSON.stringify(users) }] };
});
```

**Good — distinguishes access failure from empty result:**
```typescript
server.tool("query_users", { filter: z.string() }, async ({ filter }) => {
  try {
    const users = await db.query("SELECT * FROM users WHERE name LIKE ?", [filter]);
    // Success: query ran, return results (even if empty)
    return {
      content: [{ type: "text", text: JSON.stringify({ users, count: users.length }) }]
    };
  } catch (error) {
    // Failure: query could not run
    return {
      isError: true,
      content: [{ type: "text", text: JSON.stringify({
        errorCategory: error.code === "ETIMEDOUT" ? "transient" : "permission",
        isRetryable: error.code === "ETIMEDOUT",
        description: `Database error: ${error.message}`
      })}]
    };
  }
});
```

### 2.5 What Happens When `isError` Is Set

In Claude Code, when an MCP tool returns `isError: true`:

1. The error details are extracted from `content[0].text`
2. A `McpToolCallError` is thrown, carrying the MCP `_meta` metadata
3. The error is caught and converted to a `tool_result` with `is_error: true`
4. The model sees the error in its context and decides the next action

Importantly, error scope is controlled: only Bash tool errors cancel sibling tool executions (because shell commands often have implicit dependency chains like `mkdir` then `cd`). MCP tool errors do **not** cancel concurrent sibling operations — one MCP failure should not nuke independent parallel work.

---

## Part 3: Access Failure vs Valid Empty Result

This is the most commonly confused distinction in MCP tool design, and a high-frequency exam topic.

### 3.1 The Fundamental Rule

| Situation | Did the tool perform its operation? | `isError` | Content |
|-----------|-----------------------------------|-----------| --------|
| **Access failure** | No — could not reach the resource | `true` | Error details |
| **Valid empty result** | Yes — reached the resource, found nothing | `false` | Empty-but-valid result |

The deciding question is always: **"Did the tool successfully execute its intended operation?"** If yes, it's not an error — even if the result set is empty.

### 3.2 Anti-Pattern: Empty Results as Errors

```json
{
  "isError": true,
  "content": [{"type": "text", "text": "No matching records found"}]
}
```

This causes the agent to:
- Retry a query that will always return nothing (wasting tokens)
- Report "an error occurred" to the user when there was no error
- Potentially try alternative tools to "work around the failure"

### 3.3 Anti-Pattern: Access Failures as Empty Results

```json
{
  "isError": false,
  "content": [{"type": "text", "text": "No data available"}]
}
```

When the actual cause was a database connection failure, this causes the agent to:
- Tell the user "there's no data" when data may actually exist
- Move on to other tasks, missing a systemic failure
- Never retry an operation that would succeed once the service recovers

### 3.4 How Claude Code Handles Empty Results

Claude Code detects truly empty tool results — null, undefined, whitespace-only strings, empty arrays, arrays of empty text blocks — via `isToolResultContentEmpty()`. When content is empty, it injects a completion marker:

```
(toolName completed with no output)
```

This prevents the model from misinterpreting silence as a broken response. Your MCP tool should return a descriptive empty-but-valid message (like `"Query returned 0 matches"`) rather than relying on this fallback.

### 3.5 Decision Table

| Scenario | `isError` | Content | Agent Action |
|----------|-----------|---------|--------------|
| DB query returns 0 rows | `false` | `"0 rows matched the query"` | Report to user |
| DB connection refused | `true` | `"Connection refused: ECONNREFUSED"` | Retry or escalate |
| File not found (expected to exist) | `true` | `"ENOENT: /path/to/expected/file"` | Report to user |
| Search finds no matches | `false` | `"No files match pattern *.xyz"` | Report to user |
| Search index unavailable | `true` | `"Search service returned 503"` | Retry |
| API returns empty list | `false` | `"{ \"items\": [], \"total\": 0 }"` | Report to user |
| API authentication expired | `true` | `"401 Unauthorized: token expired"` | Prompt re-auth |
| Delete succeeded (nothing to return) | `false` | `"Deleted 3 records"` | Confirm to user |

---

## Part 4: Structured Error Metadata

### 4.1 Beyond `isError: true`

The `isError` flag tells the agent "this failed" but not "what should I do about it." Structured metadata in the error content enables intelligent decisions. Include these fields in your error response content:

```json
{
  "errorCategory": "transient | validation | business | permission",
  "isRetryable": true,
  "description": "Human-readable explanation of what went wrong",
  "retryAfterSeconds": 30,
  "userMessage": "Optional: message suitable for showing to the end user",
  "details": {}
}
```

### 4.2 Category-to-Behavior Mapping

| Category | `isRetryable` | Agent Behavior | Example Response |
|----------|--------------|----------------|------------------|
| Transient | `true` | Retry with backoff | `"Rate limited by API. Retry-After: 45s"` |
| Validation | `false` | Read `description`, correct input, re-call | `"Parameter 'date' must be ISO 8601 format, got '2024/01/15'"` |
| Business | `false` | Report `userMessage` to user | `"Refund amount ($150) exceeds original purchase ($99.99)"` |
| Permission | `false` | Report to user; may prompt re-auth | `"OAuth token expired at 2024-01-15T10:00:00Z"` |

Note: "correct and re-call" for validation errors is semantically different from "retry." A retry repeats the same call; a correction changes the input. The `isRetryable` flag should be `false` for validation errors because retrying with the same bad input will always fail.

### 4.3 Detailed Descriptions, Not Generic Messages

Claude Code's `formatError()` preserves full error details up to 10,000 characters, using a symmetric head/tail truncation strategy (first 5,000 + last 5,000 characters) for oversized errors. This ensures both the error type (usually at the start) and the specific details (often at the end) are preserved.

Follow the same principle in your MCP tool:

**Bad:**
```json
{ "description": "An error occurred" }
```

**Bad:**
```json
{ "description": "Operation failed" }
```

**Good:**
```json
{ "description": "GitHub API rate limit exceeded. 0 of 5000 requests remaining. Resets at 2024-01-15T10:30:00Z. Retry-After: 45 seconds." }
```

**Good:**
```json
{ "description": "Parameter 'file_path' validation failed: expected absolute path starting with '/', received relative path 'src/main.ts'. Hint: prepend the project root directory." }
```

### 4.4 Validation Errors: Help the Agent Self-Correct

Claude Code's `formatZodValidationError()` extracts and reports three categories of input problems:

1. **Missing required parameters** — which fields are absent
2. **Type mismatches** — expected type vs received type for each field
3. **Unexpected parameters** — which fields were provided but not defined in the schema

This gives the agent enough information to fix the call without guessing. Your MCP tool's validation errors should be equally specific:

**Bad:**
```json
{ "description": "Invalid parameters" }
```

**Good:**
```json
{
  "errorCategory": "validation",
  "isRetryable": false,
  "description": "Validation failed: missing required parameter 'project_id' (string); parameter 'limit' has wrong type (expected number, got string '10'); unexpected parameter 'verbose' is not defined in the schema"
}
```

### 4.5 Context-Aware Retry Decisions

Not all retries are equal. Claude Code's `withRetry` module makes retry decisions based on the **source of the request**:

- **Foreground requests** (user-facing, interactive): retry 429/529 errors with backoff
- **Background requests** (summarizers, classifiers): bail immediately on 429/529 to avoid cascade amplification

The lesson for MCP tool design: if your tool orchestrates sub-requests, consider whether retrying a failed sub-request is worth the cost. A background indexing operation should not retry aggressively; a user-initiated query should.

Include `retryAfterSeconds` in transient error responses when possible — it lets the agent wait the right amount of time rather than guessing.

---

## Part 5: Subagent Error Propagation

### 5.1 The Decision Rule

When a subagent encounters an error from an MCP tool:

- **Transient errors**: Handle locally. Retry with backoff before reporting failure upward. The parent agent doesn't need to know about a transient error that was resolved.
- **Non-recoverable errors**: Escalate immediately with context. The parent needs three things: what was attempted, what partial work was completed, and the error details.

### 5.2 The Partial Result Pattern

When a subagent is killed or fails mid-execution, Claude Code's `extractPartialResult()` walks backward through the agent's message history to find the most recent assistant text content. This preserves accumulated work rather than discarding everything on failure.

Apply this principle when your MCP tool orchestrates multi-step operations:

```
On failure during multi-step operation:
1. Collect results from completed steps (partial results)
2. Record which steps were attempted and their outcomes (attempt history)
3. Include the final error that caused the failure
4. Return all three as structured content with isError: true
```

**Example: A tool that fetches data from 3 APIs, where the third fails:**
```json
{
  "isError": true,
  "content": [{
    "type": "text",
    "text": "{\"errorCategory\": \"transient\", \"isRetryable\": false, \"description\": \"Exhausted 3 retries against GitHub API (429 rate limit)\", \"partialResult\": {\"jira\": {\"issues\": 12}, \"confluence\": {\"pages\": 5}}, \"attemptHistory\": [{\"source\": \"github\", \"attempt\": 1, \"error\": \"429\"}, {\"source\": \"github\", \"attempt\": 2, \"error\": \"429\"}, {\"source\": \"github\", \"attempt\": 3, \"error\": \"429\"}]}"
  }]
}
```

Note: `isRetryable: false` here because the subagent already exhausted local retries. The parent can decide whether to retry the entire operation later, but the subagent has done its due diligence.

### 5.3 Error Scope Control

When your MCP tool runs multiple independent operations in parallel, scope error propagation carefully:

- **Independent operations**: One failure should NOT cancel others. Let each complete and report individually.
- **Dependent operations**: A failure in a prerequisite step SHOULD cancel downstream steps (like Bash command chains where `mkdir` failure means subsequent commands are pointless).

Claude Code implements this distinction: only Bash tool errors trigger sibling cancellation (via `siblingAbortController.abort('sibling_error')`), because shell commands often have implicit dependency chains. Read, WebFetch, and other independent tools do not cancel siblings.

**Design principle**: Default to independent (don't cancel siblings). Only use dependent chaining when there's a clear prerequisite relationship between operations.

### 5.4 Escalation vs Local Handling Summary

| Error Type | Subagent Action | What to Include in Escalation |
|------------|----------------|-------------------------------|
| Transient (first occurrence) | Retry locally | — (don't escalate yet) |
| Transient (retries exhausted) | Escalate | Partial results + attempt history + final error |
| Validation | Escalate immediately | The specific validation error details |
| Business | Escalate immediately | The business rule explanation + user message |
| Permission | Escalate immediately | Auth error details + suggested action |

---

## Quick Reference: Error Response Checklist

When designing or reviewing MCP tool error handling, verify:

- [ ] Every error is classified into one of four categories: transient, validation, business, permission
- [ ] `isError: true` is set only for actual failures — never for valid empty results
- [ ] Valid empty results return `isError: false` with a descriptive message (not empty content)
- [ ] Access failures are never masked as empty results
- [ ] Error content includes `errorCategory`, `isRetryable`, and a human-readable `description`
- [ ] Validation errors specify which parameter failed and why (not just "invalid input")
- [ ] Error descriptions are specific and detailed, not generic ("Rate limited, retry after 45s" not "An error occurred")
- [ ] Only transient errors are marked `isRetryable: true`
- [ ] Business errors include a `userMessage` field suitable for showing to end users
- [ ] Subagent transient errors are retried locally before escalating
- [ ] Escalated errors include partial results and attempt history
- [ ] Error scope is controlled — one independent operation's failure does not cancel others

---

## See Also

- **`mcp-tool-design`** — Design-level principles for tool descriptions, input/output contracts, tool splitting, and routing. Start there when designing tool content from scratch; come here when your tool content is designed but needs proper error response patterns.
- **`mcp-tool-enhancement`** — Platform-level optimization for Claude Code: `searchHint`, `alwaysLoad`, annotations, Resources, and `.mcp.json` configuration. Go there after error handling is designed, to make your tools discoverable and competitive.
