# Fanshi Personal Skills

A Claude Code plugin marketplace containing curated skill collections for presentation generation, academic writing, tool-stack expertise, project lifecycle management, coding standards enforcement, and Claude 301 exam prep.

## Plugins

| Plugin | Description | Skills |
|--------|-------------|--------|
| **agents** | Presentation generation agent | 1 — ppt-master |
| **documents** | Academic writing & document generation | 5 — ml-paper-writing, scientific-slides, latex-posters, study-notes-generator, tailored-resume-generator |
| **general** | General-purpose utilities | 6 — find_skills, humanizer-zh, plugin-publishing, push, start_simple, web-extractor |
| **techstack** | Technical stack skills | 3 — claude-d3js-skill, langchain-architecture, langgraph |
| **sentinel** | Project lifecycle management | 10 — start, routing, boundary, progress, sentinel-loop, sentinel-export, call-codex, submit-issue, find_skills, skill-creator |
| **ant_prompt** | Anthropic-internal coding standards as hooks | 2 — install-ant-hooks, remove-ant-hooks |
| **claude_301** | Claude 301 exam preparation skills | 10 — agent-tool-allocation, ci-local-testing, domain-search-mcp-designer, mcp-error-response, mcp-tool-design, mcp-tool-enhancement, rule-creator, search-tool-schema-design, skill-builder, skill-creator |
| **sde_mattpocock** | Engineering skills for real software development (Matt Pocock) | 18 — diagnose, grill-with-docs, improve-codebase-architecture, prototype, setup-matt-pocock-skills, tdd, to-issues, to-prd, triage, zoom-out, caveman, grill-me, handoff, write-a-skill, git-guardrails-claude-code, migrate-to-shoehorn, scaffold-exercises, setup-pre-commit |
| **frontend_taste** | Anti-slop frontend design framework | 12 — taste-skill, gpt-tasteskill, soft-skill, minimalist-skill, brutalist-skill, redesign-skill, image-to-code-skill, imagegen-frontend-web, imagegen-frontend-mobile, brandkit, output-skill, stitch-skill |
| **web-access** | Web browsing & CDP browser automation | 1 — web-access |

## Structure

```
├── .claude-plugin/
│   └── marketplace.json          # Plugin registry
├── agents/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── documents/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── general/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── techstack/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── sentinel/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── ant_prompt/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── claude_301/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── sde_mattpocock/
│   ├── .claude-plugin/plugin.json
│   └── skills/<skill>/              # flat, auto-scanned (buckets flattened)
├── frontend_taste/
│   ├── .claude-plugin/plugin.json
│   └── skills/<skill>/              # flat, auto-scanned
└── web-access/
    ├── .claude-plugin/plugin.json
    └── skills/web-access/           # SKILL.md + scripts/ + references/ + templates/
```

Every skill lives in its own directory under the plugin's `skills/` folder, named after the skill, containing a `SKILL.md` (YAML frontmatter `name`, `description` + markdown instructions) plus any `scripts/`, `references/`, or `assets/` it needs. Claude Code auto-discovers every `skills/<name>/SKILL.md` — no explicit `skills` array in `plugin.json` is required.

- **sde_mattpocock** was flattened from its upstream bucketed layout (`skills/engineering/…`, `skills/productivity/…`, `skills/misc/…`) into flat `skills/<skill>/`. The upstream non-shipping buckets (`personal/`, `in-progress/`, `deprecated/`) were dropped per the upstream `CLAUDE.md` rule. Cross-skill links (e.g. `improve-codebase-architecture` → `../grill-with-docs/…`) remain valid since siblings moved up together.
- **web-access** was moved from a root-level `SKILL.md` into `skills/web-access/` with its `scripts/`, `references/`, and `templates/` alongside it (so `${CLAUDE_SKILL_DIR}` still resolves).

## Installation

Add this marketplace to Claude Code:

```bash
claude plugin add /path/to/skillsWorkSpace
```

Or from GitHub:

```bash
claude plugin add https://github.com/Touricks/fanshi_personal_skills.git
```

## Adding New Skills

1. Create a directory under the appropriate plugin's `skills/` folder
2. Add a `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: my-skill
   description: Brief description for triggering
   ---
   ```
3. Add markdown instructions in the body
4. Optionally add `scripts/`, `references/`, or `assets/` subdirectories
5. Bump the plugin's `version` in `.claude-plugin/plugin.json`

Use the `sentinel:skill-creator` skill to audit skill quality, or `skill-creator:skill-creator` (marketplace) to create new skills.
