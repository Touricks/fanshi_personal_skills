# Attribution Schema

The scaffold bakes in the attribution contract so downstream edits don't drift from Claude Code's canonical pattern. This doc explains the pieces.

## Canonical reference

- **Zod output schema:** `reference/src/tools/WebSearchTool/WebSearchTool.ts:42-54` — each result is `{ title, url }`.
- **Mandatory `Sources:` section:** `reference/src/tools/WebSearchTool/prompt.ts:14-24` — "You MUST include a `Sources:` section … This is MANDATORY".
- **125-character excerpt cap:** `reference/src/tools/WebFetchTool/prompt.ts:28-34` — quotation marks required for verbatim language.

These requirements were lifted into this scaffold's `schemas.py` (Pydantic models), `writeback.py` (Sources section emission + long-unquoted-span check), and `server.py` (fetch_detail docstring warns about the 125-char rule).

## Pydantic models

```python
class SearchResult(BaseModel):
    title: str
    url: HttpUrl
    snippet: str = ""
    source_language: str = "<primary_lang>"
    retrieved_at: datetime

class DetailResult(BaseModel):
    url: HttpUrl
    title: str
    body: str
    quotations: list[Quotation]
    retrieved_at: datetime

class Quotation(BaseModel):
    text: str
    context: str | None

class ScratchpadMeta(BaseModel):
    query: str
    translated_query: str
    query_hash: str
    backend: str
    created_at: datetime
```

The contract each model enforces:
- **SearchResult.url** is `HttpUrl`, not `str`. Catches bad URLs at construction, not at the Sources rendering step (where a bad URL would silently produce a broken hyperlink).
- **SearchResult.source_language** records the language of `title` and `snippet` after any translation — important for multi-domain aggregations where the comprehensive report might mix Chinese and English sources.
- **Quotation.text** is the verbatim span. Writeback enforces quotation marks on ≥ 15-word spans; entries that fail the check produce a warning banner in the aggregate report.
- **ScratchpadMeta.translated_query** is preserved so the writeback step can surface "you asked X in English; we queried Y in Chinese" when the two diverge meaningfully.

## Report format

The writeback tool produces exactly one markdown document per query. Structure:

```
# Report: <original query>

> **Attribution warnings:** (optional — only if quotation checks fired)
> - https://…: long unquoted span (23 words) — wrap verbatim excerpts in quotation marks.

## <source 1 title>

<body of summary 1>

## <source 2 title>

<body of summary 2>

…

## Sources
- [<source 1 title>](<url 1>)
- [<source 2 title>](<url 2>)
…
```

Rules the writeback step enforces, in order:

1. **The `## Sources` section must be present.** This is the non-negotiable bit. If zero summaries were written, the report still emits a `## Sources` heading with an empty list — this makes the absence of sources visible rather than ambiguous.
2. **Every Sources entry is a markdown hyperlink `[title](url)`.** Matches the format in Claude Code's canonical prompt.
3. **Every source in the body corresponds one-to-one with a Sources entry.** No orphan claims; no orphan sources.

## Why not just compose this at the LLM layer?

Because the LLM will eventually forget — under long context, with many tool calls, under compaction. Baking the Sources section into the writeback tool's code means the section exists whether or not the calling agent remembered to ask for it. This mirrors the WebSearchTool's choice to inject a REMINDER into the `tool_result` payload itself (`reference/src/tools/WebSearchTool/WebSearchTool.ts:401-434`) — trust the machinery, not the model's memory.

## Verifying attribution in practice

Spot-check one generated report per domain when you first ship:

```bash
# Should return non-empty
grep -c "^## Sources" report.md

# Every body header should map to a Sources line
awk '/^## / && !/^## Sources/ { print $0 }' report.md | wc -l
awk '/^- \[/' report.md | wc -l   # should equal the above (modulo the query title)
```

If the counts diverge, something wrote to the scratchpad without going through `append_summary`, or the writeback tool was modified. Don't patch around it — find the bypassing writer.
