# Fanshi Personal Skills

A Claude Code plugin marketplace containing curated skill collections for ML writing, project lifecycle management, coding standards enforcement, and more.

## Plugins

| Plugin | Description | Skills |
|--------|-------------|--------|
| **original** | General-purpose skill collection | 19 — ml-paper-writing, scientific-slides, latex-posters, pdf, docx, xlsx, humanizer, web-extractor, push, skill-creator, plugin-publishing, and more |
| **sentinel** | Project lifecycle management | 7 — start, routing, boundary, progress, sentinel-loop, sentinel-export, call-codex |
| **ant_prompt** | Anthropic-internal coding standards as hooks | 2 — install-ant-hooks, remove-ant-hooks |

## Structure

```
├── .claude-plugin/
│   └── marketplace.json          # Plugin registry
├── original/
│   ├── .claude-plugin/plugin.json
│   └── skills/
├── sentinel/
│   ├── .claude-plugin/plugin.json
│   └── skills/
└── ant_prompt/
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

See the `skill-creator` skill in the original plugin for detailed guidance.
