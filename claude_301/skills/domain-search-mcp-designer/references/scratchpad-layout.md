# Scratchpad Layout

The scratchpad is where sub-agents (and direct tool calls) stage individual source summaries before they're composed into a final report. It's the concrete realization of Task 5.6 Skill S1 from the Claude 301 review — "require sub-agents to output structured claim-source mappings".

## Directory structure

```
<project-root>/.search-scratchpad/
├── README.md                    # written at scaffold time
├── <qhash>/                     # sha1(original query)[:10]
│   ├── meta.json                # ScratchpadMeta
│   ├── 001-<host>.md            # per-source summary with front-matter URL
│   ├── 002-<host>.md
│   └── …
└── <other qhash>/
    └── …
```

Each `<qhash>/` corresponds to one top-level user search. Files inside are append-only during a single search; the writeback step reads them all in order when composing the final report.

## `meta.json` format

```json
{
  "query": "late-night ramen Brooklyn",
  "translated_query": "深夜 拉面 布鲁克林",
  "query_hash": "c9f2a1e4b2",
  "backend": "playwright",
  "created_at": "2026-04-16T21:07:03.412817"
}
```

This is the Pydantic `ScratchpadMeta` model serialized. Keep it stable — the writeback step reads `query` for the report's H1, and downstream analysis tools grep across many scratchpads looking for `backend`/`translated_query` patterns.

## Per-source summary format

Each summary file has YAML front-matter (not TOML, not JSON — just three fields, so a tiny regex reads it) followed by markdown body:

```
---
source_url: https://www.xiaohongshu.com/discovery/item/abc123
source_title: 深夜拉面测评：布鲁克林最香的一家
written_at: 2026-04-16T21:08:12.004231
---

小红书博主探访了布鲁克林 Williamsburg 区的 Chuko Ramen。核心观点：

- "汤头偏甜但后味有深度" (user quotation from the post)
- 强调店家在深夜时段仍然保持品质
- 附地址：552 Vanderbilt Ave, Brooklyn

博主建议: 工作日晚 11 点后最空。
```

The body is the sub-agent's summary — **not** the raw page content. Keep it short (200–500 words is a good range). Anything longer and the writeback step produces a fatigue-inducing final report.

Verbatim excerpts belong in quotation marks (Chinese quotes `""` or English `""`, either works — the writeback's quotation check matches both). Anything ≥ 15 words without quotes triggers a warning.

## Garbage collection

Scratchpads accumulate. `scratchpad.gc()` removes per-query directories older than seven days (tuneable). Call it:

- From a cron job, if the server runs long-lived.
- At server startup, if the server is short-lived — cheap and keeps disk bounded.
- Never from inside a search — GC and writes racing is not worth the complexity.

## Concurrency

**Writes are not locked.** If two sub-agents target the same `<qhash>/` simultaneously, they get distinct numbered files (the number is allocated via `glob + len + 1`, which has a race window, but in practice the collision rate is negligible and the writeback step deduplicates by URL). If your workload has genuine concurrent writes to a single query, wrap `append_summary` in a file lock (`fcntl.flock`) — deliberately not done in the scaffold to keep the default simple.

## Cross-process shared state

The scratchpad is filesystem-based on purpose. A SQLite/Postgres-backed version would handle concurrency better but loses:

- Direct inspection (`ls .search-scratchpad/<qhash>/` to see what's there).
- Trivial portability across machines (`rsync` the dir to reproduce a session).
- Zero-setup initial use.

If you hit a case where those tradeoffs reverse (high concurrency, multi-machine, large summaries), swap the scratchpad module's implementation behind the same `init_scratchpad` / `append_summary` / `list_summaries` interface — the writeback tool only depends on that surface.

## Link to Task 5.6

Task 5.6 S1 ("require sub-agents to output structured claim-source mappings") and S3 ("preserve conflict values and let the coordinator reconcile") both assume a per-source intermediate staging layer. This is it. When two sources report conflicting values (different prices, different hours), **write both summaries** — don't have the sub-agent pick one. The writeback step's `## Sources` section makes the disagreement visible; the aggregate reader can judge which source to trust.
