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
└── claude_301/
    ├── .claude-plugin/plugin.json
    └── skills/
```

Each skill lives in its own directory under `skills/` with a `SKILL.md` file containing YAML frontmatter (`name`, `description`) and markdown instructions.

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
