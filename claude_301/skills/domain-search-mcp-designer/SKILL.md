---
name: domain-search-mcp-designer
description: >
  Scaffold a Python FastMCP server for domain-specific authenticated web search
  (Xiaohongshu, Dianping, Weibo, LinkedIn, NYT, region-locked forums, etc.)
  where the user's browser session supplies auth. Produces a working server
  skeleton with four wired-in features: Playwright-MCP browser bridge (with
  Claude-in-Chrome fallback), EN-to-domain-native query translation, per-search
  scratchpad directory, and structured writeback with source attribution.
  ALWAYS use this skill when the user says "build an MCP server for <site>",
  "scaffold a search MCP", "domain search server", "FastMCP server for <site>",
  "search scraper MCP", or asks to wrap a site behind an MCP search tool. Do
  NOT hand-write a FastMCP search server — invoke this skill so attribution,
  scratchpad layout, and backend selection stay consistent. For generic MCP
  tool shape guidance, see mcp-tool-design; for search result schema, see
  search-tool-schema-design.
---

# Domain Search MCP Designer

Scaffold a Python FastMCP server that wraps an authenticated domain (Xiaohongshu, Dianping, LinkedIn, NYT, Weibo, …) behind a small, attribution-aware search interface. The user's browser session supplies auth — this skill does **not** generate login code.

## Why This Skill Exists

Every domain-specific search MCP tends to rediscover the same four problems: (1) how to reach the site through a browser (Playwright vs. an already-logged-in Chrome), (2) how to translate upstream English queries into the site's native language, (3) where to stage intermediate findings so sub-agents can contribute, and (4) how to preserve claim-to-source mapping when summarizing into a final report.

The canonical answers live in Claude Code's own `WebSearchTool` — Zod-enforced `title` + `url` on every result, a mandatory `Sources:` section in every response, and a 125-character cap on verbatim excerpts. This skill bakes those answers into a working skeleton so you don't re-derive them per domain.

Hand-rolled versions drift: attribution becomes a string-concat afterthought, the scratchpad grows unbounded, translator logic gets pasted inline. A shared scaffold keeps these consistent across domains and lets downstream developers focus on the two places that genuinely need per-domain thought: the selector logic and the credential storage policy.

## Input

A short natural-language request naming the target domain and (optionally) the browser backend and translation language. Example:

> "Scaffold an MCP server for Xiaohongshu POI search in LA. Use Playwright for the browser."

## Workflow

### Phase 1: Design Interview

Ask the user for the three required answers. Do not assume — wrong assumptions here cascade through every generated file.

1. **Target domain** — the canonical host (e.g., `xiaohongshu.com`, `dianping.com`, `linkedin.com`) and a short human name for the package (e.g., `Xiaohongshu`, `Dianping`).
2. **Primary content language** — the ISO-639-1 code for the language the domain's content and search index actually use (`zh`, `ja`, `ko`, `en`, …). This drives the translator target.
3. **Browser backend** — `playwright` (clean-slate, default) or `claude_in_chrome` (fallback, uses the user's already-logged-in Chrome session). If the user is unsure, show them the tradeoff table from `references/playwright-vs-claude-in-chrome.md` and let them choose.

Two conditional follow-ups:

4. If backend is `playwright` **and** the target domain requires login — ask where the user will keep their Playwright storage-state JSON at runtime (e.g., `~/.config/<server_pkg>/storage_state.json`). Do not attempt to create or populate it.
5. If translation is ambiguous (e.g., English site with English upstream queries) — ask whether the translator should be `identity` (pass through), `dictionary` (local lookup), or `llm` (call a downstream model). Default to `identity` when source and target languages match.

### Phase 2: Confirm Config

Print a confirmation table. Do not materialize anything until the user confirms.

```
| Field              | Value                          |
|--------------------|--------------------------------|
| domain_name        | Xiaohongshu                    |
| domain_host        | xiaohongshu.com                |
| server_pkg         | xhs_search                     |
| primary_lang       | zh                             |
| browser_backend    | playwright                     |
| translator_mode    | llm                            |
| storage_state_path | ~/.config/xhs_search/state.json|
| output_dir         | ./xhs-search/                  |
```

Include a two-line reminder of the chosen backend's implication:
- `playwright`: "Clean slate — you will need to produce `storage_state.json` yourself via one `playwright codegen` session."
- `claude_in_chrome`: "Uses your already-logged-in Chrome. More cookies, wider access, looser isolation — read `references/playwright-vs-claude-in-chrome.md` before shipping."

### Phase 3: Scaffold

Materialize the scaffold deterministically via the bundled script.

1. Verify `output_dir` is empty (or the user has passed `--force`). If not, stop and report.
2. Write `scaffold_config.json` into a temp path with the confirmed answers. Required keys: `domain_name`, `domain_host`, `server_pkg`, `primary_lang`, `browser_backend`, `translator_mode`. Optional: `storage_state_path`, `python_path`.
3. Invoke:
   ```
   python <skill>/scripts/scaffold.py --config <tmp>/scaffold_config.json --out <output_dir>
   ```
4. Read the script's stdout. On exit code `0`, it prints a TODO checklist — relay it verbatim to the user. On non-zero, surface the reported error (config invalid / out-dir non-empty / template IO) and help the user fix the config, then re-run.

### Phase 4: Validate

Run the post-scaffold validator:

```
python <skill>/scripts/validate_scaffold.py <output_dir>
```

This imports the generated package, round-trips the Pydantic `SearchResult`, and confirms `.search-scratchpad/` exists. If any check fails, walk the TODO checklist — the common cause is a missing Python dep (`uv pip install -e .` in the scaffold dir).

### Phase 5: Handoff

Surface to the user, in order:

1. **Client registration** — copy the block from `<output_dir>/mcp_config.json` into their MCP client config (Claude Code, Claude Desktop, etc.).
2. **Scratchpad location** — point at `<output_dir>/.search-scratchpad/`. Explain that each search creates a `<qhash>/` subdirectory with `meta.json` + per-source summary files. Sub-agents write summaries here; the writeback tool reads them to produce the final report.
3. **Remaining TODOs** — re-print the checklist from Phase 3. The biggest ones:
   - Credential storage strategy (cookies expire; pick a refresh plan — read `references/playwright-vs-claude-in-chrome.md#auth-surface`)
   - Translator tuning (the stub works; replace it with domain-appropriate rules — read `references/query-translation-patterns.md`)
   - Rate-limit policy (each domain has its own anti-scraping posture)

## Rules

These three are non-negotiable. They exist because each has been violated enough times in hand-rolled servers to cause real incidents.

- **Never generate credential or login code.** The skill assumes browser cookies handle auth. For any field the server would need (username, password, OTP code, API key), emit a `TODO: credential storage` comment with a link to `references/playwright-vs-claude-in-chrome.md#auth-surface` and stop. Downstream developers own the credential surface; auto-generating it creates security footguns and brittle selectors.
- **Every search-returning tool must return a Pydantic `SearchResult` from `schemas.py`.** No ad-hoc dicts. The `title` + `url` pair is what makes the `Sources:` section reliable — if it drifts to a dict, the writeback tool's attribution breaks silently. This mirrors `reference/src/tools/WebSearchTool/WebSearchTool.ts:42-54`.
- **The writeback tool MUST emit a `## Sources` markdown section** with URL + title per claim. This mirrors the `CRITICAL REQUIREMENT` at `reference/src/tools/WebSearchTool/prompt.ts:14-24`. The generated `writeback.py` enforces this — do not let it be removed in downstream edits.

## Key Paths

- Plugin root: `skillsBuilder/claude_301/`
- Skill: `skillsBuilder/claude_301/skills/domain-search-mcp-designer/`
- Scaffold script: `skillsBuilder/claude_301/skills/domain-search-mcp-designer/scripts/scaffold.py`
- Templates: `skillsBuilder/claude_301/skills/domain-search-mcp-designer/templates/`
- Reference docs (read on demand): `skillsBuilder/claude_301/skills/domain-search-mcp-designer/references/`

## See Also

- `mcp-tool-design` — how to write tool descriptions that LLMs route to reliably
- `search-tool-schema-design` — input schema patterns for search-type tools
- `mcp-tool-enhancement` — `searchHint`, `alwaysLoad`, `annotations`, `.mcp.json` config
- `skill-builder` — how this skill itself was structured
- `reference/src/tools/WebSearchTool/prompt.ts` — canonical source for the `Sources:` attribution requirement
- `reference/src/tools/WebFetchTool/prompt.ts` — 125-character quotation rule
