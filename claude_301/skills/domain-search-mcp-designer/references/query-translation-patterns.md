# Query Translation Patterns

The translator sits between the upstream agent (usually English) and the target domain's native search. Three patterns ship with the scaffold.

## Identity

**When to use:** upstream and domain share a language (e.g., LinkedIn in English, upstream also English).

**Failure mode:** none, practically. This is the default "no translation" path.

Selected via `translator_mode=identity` at scaffold time. The stub lives in `translator.py:IdentityTranslator`.

## Dictionary

**When to use:** small, closed vocabularies. POI categories on Xiaohongshu ("ramen", "coffee", "bookstore"). Cuisine types on Dianping. Equipment names on a vertical forum.

**Failure mode:** dialect drift (Mandarin → Cantonese variant), proper-noun leakage (neighborhood names), polysemy ("Apple" → 苹果 the fruit vs. 苹果 the company). The dictionary has no context.

Selected via `translator_mode=dictionary`. The stub in `translator.py:DictionaryTranslator` ships an illustrative `DICT` of three entries — **extend it** before using.

## LLM

**When to use:** open-ended queries, dialect handling, proper-noun preservation, slang. Anything where context matters.

**Failure mode:** latency (+500ms to +2s per query), cost, API-key dependency. Also: the LLM may "improve" a query past the point where it matches the domain's actual indexing — a query that worked great on ChatGPT can return zero hits on the target site.

Selected via `translator_mode=llm`. The stub in `translator.py:LLMTranslator` raises `NotImplementedError` by design — wire it to your preferred client (Claude, OpenAI, local model) before use.

## A worked example: Xiaohongshu EN→ZH

Upstream query: `late-night ramen Brooklyn`

| Translator | Output                                      | Notes |
|------------|---------------------------------------------|-------|
| Identity   | `late-night ramen Brooklyn`                 | Xiaohongshu will return zero results — its index is Chinese-only. |
| Dictionary | `深夜 拉面 布鲁克林`                         | Works. The three-entry stub dictionary happens to cover these exact tokens. |
| LLM        | `布鲁克林深夜拉面` / `纽约布鲁克林拉面推荐`    | Better — idiomatic phrasing, may surface higher-quality results. Non-deterministic; can drift between runs. |

The LLM's second variant (`纽约布鲁克林拉面推荐` — "New York Brooklyn ramen recommendations") is the kind of output where the LLM "helped" by adding location context and an explicit "recommendations" suffix. Whether that helps or hurts depends on the site's actual indexing. This is why `ScratchpadMeta.translated_query` records what was actually sent — so the writeback step can surface the gap between the user's intent and the query that produced results.

## Translator system prompts

If you use the LLM path, the system prompt matters. Bad:

> "Translate this query to Chinese."

Good (what the scaffold's `LLMTranslator.SYSTEM_PROMPT` uses as a starting point):

> "You translate search queries into `<primary_lang>` for `<domain_name>`. Preserve proper nouns. Use the site's native slang where appropriate. Return only the translated query, no commentary."

Better (domain-specific, to write after you ship):

> "You translate English search queries into Mandarin Chinese for Xiaohongshu (小红书), a Chinese lifestyle content platform. Users search for restaurants, neighborhoods, products, experiences. Preserve:
> - English brand names (Apple, Uniqlo)
> - Latin-script neighborhood names only if untranslatable (Williamsburg → 威廉斯堡 OK; SoHo → stay as SoHo)
> - Numbers
> Use casual, searchy phrasing — not formal written Mandarin. Return ONLY the translated query."

## Translation is not identification

A common mistake: treating the translated query as if it were the user's intent. It isn't — it's a lossy projection of the intent into the target's query language. The writeback report should reflect the user's original query in the `# Report:` heading and mention the translated query only when it materially differs. The ScratchpadMeta records both; use it.
