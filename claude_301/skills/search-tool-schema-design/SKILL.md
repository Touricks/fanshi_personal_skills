---
name: search-tool-schema-design
description: >
  Design input and output JSON Schemas for search or retrieval tools that query
  the web, databases, code indexes, vector stores, or external services. Use
  when designing, reviewing, or refactoring a search-result tool, even if the
  user does not say "schema". Covers required vs optional/nullable fields, empty
  results, missing metadata, truncation/pagination (`appliedLimit` vs
  `truncated`), heterogeneous results (`z.union` and discriminated unions), enum
  `other` vs `unclear`, and HTTP metadata. Trigger on "search tool",
  "database/web/vector search", "retrieval output schema", "pagination",
  "truncation", "no results", "nullable fields", "enum other/unclear", or
  hallucinated missing fields. For general tool description or splitting, use
  `mcp-tool-design`; for error shapes, use `mcp-error-response`.
---

# Search Tool Schema Design

Designing the schema for a search-type tool is different from designing the schema for a transformation or write tool. Search tools must honestly report four uncomfortable realities:

1. The query may return nothing.
2. Some per-result metadata may be missing from the upstream source.
3. The result set may be truncated.
4. The shape of a result may depend on the operation mode.

Schemas that ignore these realities force the model to hallucinate values to satisfy them. This skill is a pattern library for schemas that tell the truth.

All examples use [Zod](https://zod.dev) as a concrete notation, but every pattern has a direct JSON Schema equivalent.

---

## Part 1 — The core principle: fewer `required` fields, more `nullable`

Every field you mark `required` is a promise that the model **always** has a value for it. When the upstream source (a web page, a database row, a log line) doesn't contain that value, the model has two bad choices: skip the field and violate the schema, or invent a plausible value to satisfy the schema. Models overwhelmingly choose the second option.

The fix is boring but decisive: **default to optional / nullable, make required the exception**. The only truly required fields in a search-tool response are the ones that identify what was searched and how long it took — the **operation metadata**, not the per-result metadata.

**Why required vs optional / nullable matters so much for search tools:**
- Search-type tools forward information from an external source. The tool cannot fabricate what the source didn't give it.
- Required fields are a **design claim** that the source always contains this data. If that claim is wrong even 1% of the time, the model will fill the gap with plausible nonsense 1% of the time.
- Nullable fields are a **valuable signal** to the downstream consumer: `null` means "I looked and it's not there", which is genuinely different from "I didn't look".

**Pattern — only operation identity is required:**

```typescript
const inputSchema = z.strictObject({
  query: z.string().min(2).describe('The search query to use'),
  allowed_domains: z
    .array(z.string())
    .optional()                                // ← filters are optional
    .describe('Only include search results from these domains'),
  blocked_domains: z
    .array(z.string())
    .optional()                                // ← filters are optional
    .describe('Never include search results from these domains'),
})
```

**Pattern — optional metadata counts that only apply in some cases:**

```typescript
const outputSchema = z.object({
  operation: z.enum([/* e.g. goToDefinition, findReferences, ... */]),
  result:    z.string(),
  filePath:  z.string(),
  resultCount: z.number().int().nonnegative().optional(), // ← only meaningful
  fileCount:  z.number().int().nonnegative().optional(),  //    for some ops
})
```

`resultCount` is optional because it's meaningful for "find references" / "workspace symbol search" but nonsensical for "go to definition" (which returns exactly one thing). Don't force the field to exist just to make the schema "uniform" — that forces the model to invent a value when it shouldn't.

---

## Part 2 — Representing absence: three ways to say "no value"

Every schema should distinguish three different meanings of "absent". Conflating them is a common bug.

| Construct | Semantics | Use for |
|-----------|-----------|---------|
| **Empty array `[]`** | "We searched and found nothing." This is a successful outcome. | Result lists (`results`, `hits`, `matches`). |
| **Explicit `null`** (via `.nullable()`) | "The record exists, but this particular field is not present on the source." | Per-result metadata that the upstream service sometimes provides (author, published_date, thumbnail). |
| **Field omitted** (via `.optional()`) | "This field doesn't apply in this response variant at all." | Mode-specific or operation-specific fields (e.g., `numMatches` only makes sense in `count` mode). |

**Do not** use `null` as a sentinel for "no results" and **do not** leave `results` field-omitted to mean empty. `results: []` is unambiguous, machine-checkable, and aligns with the model's intuition.

**Example — mode-specific fields use `.optional()`, per-result fields use `.nullable()`:**

```typescript
const outputSchema = z.object({
  mode: z.enum(['content', 'files_with_matches', 'count']).optional(),
  numFiles: z.number(),                     // always known
  filenames: z.array(z.string()),           // [] when no matches
  content: z.string().optional(),           // only in 'content' mode
  numLines: z.number().optional(),          // only in 'content' mode
  numMatches: z.number().optional(),        // only in 'count' mode
  appliedLimit: z.number().optional(),      // only when truncated
  appliedOffset: z.number().optional(),     // only when truncated
})
```

Notice how the schema *shape* communicates the tool's semantics: reading it top-to-bottom, you can tell which fields are universal and which are conditional.

---

## Part 3 — Truncation and pagination in output schemas

Search tools almost always need some kind of limit, and the schema needs to tell the model (a) when truncation happened and (b) what to do about it. Two patterns dominate; pick based on whether your tool supports offset-based continuation.

### Pattern 3a — Semantic truncation signal (`appliedLimit` / `appliedOffset`)

Output fields `appliedLimit` and `appliedOffset` are **both `.optional()` and only set when truncation actually occurred**. When the result fits within the limit, both fields are omitted. When truncation happens, the model sees the fields and knows it can paginate with a new `offset`.

```typescript
function applyHeadLimit<T>(
  items: T[], limit: number | undefined, offset: number = 0,
): { items: T[]; appliedLimit: number | undefined } {
  if (limit === 0) {
    // Explicit 0 = unlimited escape hatch
    return { items: items.slice(offset), appliedLimit: undefined }
  }
  const effectiveLimit = limit ?? DEFAULT_HEAD_LIMIT
  const sliced = items.slice(offset, offset + effectiveLimit)
  // Only report appliedLimit when truncation actually occurred, so the model
  // knows there may be more results and can paginate with offset.
  const wasTruncated = items.length - offset > effectiveLimit
  return { items: sliced, appliedLimit: wasTruncated ? effectiveLimit : undefined }
}
```

The **semantic** part matters: reading the output, the model can distinguish "I asked for 100 and got 73" (no `appliedLimit`, no more results) from "I asked for 100 and got 100" (`appliedLimit: 100`, there may be more).

### Pattern 3b — Boolean `truncated` flag

A single boolean `truncated: boolean` (always present) with a hardcoded ceiling. Simpler to implement, but loses offset information.

```typescript
const outputSchema = z.object({
  durationMs: z.number(),
  numFiles: z.number(),
  filenames: z.array(z.string()),
  truncated: z.boolean()
    .describe('Whether results were truncated (limited to 100 files)'),
})
```

### Choosing between them

| Your tool… | Use |
|-----------|-----|
| Supports offset-based continuation (you can ask for the next page) | Semantic: `appliedLimit` / `appliedOffset` optional-when-truncated |
| Has a hard ceiling and no pagination | Boolean: `truncated: boolean` |
| Wants to let callers disable the limit | Add the "explicit 0 = unlimited" escape hatch (see `applyHeadLimit` above) |

Avoid mixing the patterns — don't ship a boolean `truncated` *and* `appliedLimit`; they carry overlapping but slightly different semantics and callers will disagree on which to trust.

---

## Part 4 — Heterogeneous results: unions and discriminated unions

Search tools frequently return **more than one shape of thing** in the same response. Schemas need to reflect that directly rather than flattening everything into a lowest-common-denominator string.

### `z.union()` — mixed structured hits and commentary

A web search tool often returns both structured search results (title + url) and free-text commentary in the same `results` array. Use `z.union()` so both shapes are valid elements:

```typescript
const searchHitSchema = z.object({
  title: z.string(),
  url:   z.string(),
})

const searchResultSchema = z.object({
  tool_use_id: z.string(),
  content:     z.array(searchHitSchema),
})

const outputSchema = z.object({
  query:   z.string(),
  results: z.array(z.union([searchResultSchema, z.string()]))
             .describe('Search results and/or text commentary from the model'),
  durationSeconds: z.number(),
})
```

This is the right move when the elements are genuinely different kinds of thing. The alternative — packing everything into a single string — destroys structure the consumer will have to re-parse.

### `discriminatedUnion` — multi-operation search tools

When the same tool serves multiple search modes that take **different inputs**, use a discriminated union on an `operation` enum. Zod (and JSON Schema `oneOf` with a discriminator) will validate each variant independently.

```typescript
const inputSchema = z.discriminatedUnion('operation', [
  goToDefinitionSchema,
  findReferencesSchema,
  hoverSchema,
  documentSymbolSchema,
  workspaceSymbolSchema,
  // ... one schema per supported operation
])
```

Each variant can have its own required fields — e.g., `goToDefinitionSchema` requires a symbol + position, while `workspaceSymbolSchema` requires only a query string. A single flat schema with fifteen optional fields, one per operation, would give the model no guidance about which combinations are valid.

**Rule of thumb:** if your tool has a `mode` / `operation` enum and different modes need different inputs, use a discriminated union. If the modes take the same inputs but return different outputs, keep a flat input schema and vary the output shape by mode.

---

## Part 5 — `"other"` vs `"unclear"` + detail

Enum fields often need an escape valve. Two distinct escape valves exist, and they are **not interchangeable**. Conflating them is one of the most common schema-design mistakes.

| Value | Means | Pair with |
|-------|-------|-----------|
| `"other"` | "This is a real category, just not in my predefined list." | A `_detail: string.nullable()` field so the model can describe the new category. |
| `"unclear"` | "I do not have enough information to classify." | Nothing, or a separate `reason: string` field. Do **not** pair with `_detail`, since the point is there's nothing to detail. |

**Example 1 — `"other"` as a long-tail catch-all (extensible categorization):**

```typescript
z.object({
  source_type: z.enum(['academic', 'news', 'forum', 'official_docs', 'other']),
  source_type_detail: z.string().nullable()
    .describe('When source_type === "other", a short description of the actual source type; otherwise null.'),
})
```

**Example 2 — `"unclear"` as an uncertainty escape (no detail needed):**

```typescript
z.object({
  outcome: z.enum([
    'not_achieved',
    'partially_achieved',
    'mostly_achieved',
    'fully_achieved',
    'unclear_from_transcript',    // ← I can't tell, not "a new category"
  ]),
})
```

The naming is deliberate: `unclear_from_transcript` is more specific than a bare `unclear` — it tells the model *why* it's unclear (the source didn't have enough information). Prefer the specific form when you can.

**Why not just make the field optional / nullable instead?** Because `null` says "no value", which loses the distinction between "new category" and "I don't know". Keeping `"other"` and `"unclear"` as enum values forces the model to make a conscious classification choice and preserves that choice in the output.

---

## Part 6 — HTTP / external-service metadata

If your tool calls out to a remote HTTP service, the output schema should include **the service's own metadata** so the model can reason about what happened without guessing. Status code, byte size, duration, and the final URL (post-redirect) all belong in the output.

```typescript
const outputSchema = z.object({
  bytes:      z.number().describe('Size of the fetched content in bytes'),
  code:       z.number().describe('HTTP response code'),
  codeText:   z.string().describe('HTTP response code text'),
  result:     z.string().describe('Processed result from applying the prompt to the content'),
  durationMs: z.number().describe('Time taken to fetch and process the content'),
  url:        z.string().describe('The URL that was fetched (post-redirect)'),
})
```

**Success vs error — keep the paths separate.** Do not pack an error into a degraded success response. A 404 with `result: ""` is ambiguous — was the page empty, or did we fail? Instead:

- **HTTP succeeded, no matching content:** successful response, `results: []` (Part 2).
- **HTTP failed (4xx / 5xx, DNS error, timeout):** error path (typically an exception or an error-shaped result — see `mcp-error-response` for the full pattern).

Including `durationMs` even on success has non-obvious value: it lets the model decide whether a slow tool is worth retrying and gives the caller basic observability for free.

---

## Part 7 — Checklist for a search-tool output schema

Before finalizing any search-tool schema, walk this checklist. Each item is a pattern from Parts 1–6.

- [ ] **Required fields are minimal** — only the query/operation identity, not per-result metadata. (Part 1)
- [ ] **Per-result metadata is `.nullable()`** unless the upstream service guarantees it. (Part 1)
- [ ] **Empty results are a valid success** — `results: []`, not `null`, not an error. (Part 2)
- [ ] **Mode-specific fields are `.optional()`**, not required-with-defaults. (Part 2)
- [ ] **Truncation is signaled** — semantic `appliedLimit` OR boolean `truncated`, but not both. (Part 3)
- [ ] **Explicit-0 escape hatch** exists for "no limit" if the tool is used from within an agent loop. (Part 3)
- [ ] **Mixed result types use `z.union()`** — structured hits + free text, not a flattened string. (Part 4)
- [ ] **Multi-operation tools use `discriminatedUnion`** on the operation field. (Part 4)
- [ ] **Open-ended categorical fields have `"other"` + `<field>_detail: string.nullable()`**. (Part 5)
- [ ] **Uncertainty is represented as its own enum value** (`"unclear"` / `"unclear_from_transcript"`), not conflated with `"other"`. (Part 5)
- [ ] **HTTP / service metadata present** — `code`, `bytes`, `durationMs`, `url` for remote fetches. (Part 6)
- [ ] **Error path is separate** from empty-result path. (Part 6)
- [ ] **Every field has `.describe()`** — and the describe string says *when* the field is set, not just what it means.

---

## See also

- **`mcp-tool-design`** — writing the tool *description* (how LLMs pick between tools), splitting responsibilities across tools, avoiding misrouting. This skill complements that one by focusing specifically on the shape of the data rather than the shape of the description.
- **`mcp-error-response`** — error-response design, the distinction between `isError: true` tool results and protocol-level errors, structured error codes. Use when designing the error path referenced in Part 6.
- **`agent-tool-allocation`** — when a search tool is one of many exposed to an agent, how to configure `tool_choice` and which agent should own the tool.
