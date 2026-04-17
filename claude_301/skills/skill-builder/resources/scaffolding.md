# Scaffolding Reference

How to validate, create, and populate a new skill directory within `skillsBuilder/claude_301/skills/`.

---

## Skill Anatomy

Every skill under this plugin follows this structure:

```
skillsBuilder/claude_301/skills/{skill-name}/
├── SKILL.md              # Required — frontmatter + workflow instructions
├── scripts/              # Optional — executable scripts the skill invokes via Bash
├── resources/            # Optional — static reference files the skill reads
└── templates/            # Optional — file templates the skill generates from
```

| Directory | Purpose | When to include |
|-----------|---------|-----------------|
| `scripts/` | Shell/Python scripts for automation | Skill needs to run external commands, setup, or data processing |
| `resources/` | Read-only reference data (prompts, schemas, examples) | Skill consults static data at runtime |
| `templates/` | File templates with placeholders | Skill generates new files from a pattern |

---

## Step 1: Validate and Normalize

1. Normalize the skill name to kebab-case: lowercase, replace spaces and underscores with hyphens. Skill names **cannot contain underscores** — reject and re-prompt if the user provides one like `my_skill` (correct form: `my-skill`)
2. Check if `skillsBuilder/claude_301/skills/{skill_name}/` already exists
   - If yes: ask the user — overwrite or pick a different name?
3. Parse which subdirs the user requested (default: none)

---

## Step 2: Create Directory Structure

1. Create the skill directory:
   ```
   mkdir -p skillsBuilder/claude_301/skills/{skill_name}/
   ```
2. For each requested subdir, create it:
   ```
   mkdir -p skillsBuilder/claude_301/skills/{skill_name}/scripts/
   mkdir -p skillsBuilder/claude_301/skills/{skill_name}/resources/
   mkdir -p skillsBuilder/claude_301/skills/{skill_name}/templates/
   ```

---

## Step 3: Generate SKILL.md

1. Read the template from `templates/skill_template.md` within the skill-builder's base directory
2. Replace placeholders with the user's inputs:
   - `{{skill_name}}` → the kebab-case skill name
   - `{{skill_description}}` → the user's description (must include trigger phrases like "Use when the user says...")
   - `{{skill_title}}` → title-cased version of the skill name
   - `{{summary}}` → one-sentence summary derived from the description
   - `{{input_description}}`, `{{step_N_title}}`, `{{substep}}` → populate with meaningful content if the user provided a workflow hint, otherwise leave as descriptive placeholders
   - `{{additional_rule}}`, `{{additional_path}}` → leave as placeholders for the user to fill in
3. Apply design decisions to the frontmatter:
   - Add `context: fork` if chosen
   - Add `allowed-tools` list if chosen
   - Add `arguments` and `argument-hint` if chosen
   - Add `agent` field if the skill uses a specific agent type
4. Write the populated SKILL.md to `skillsBuilder/claude_301/skills/{skill_name}/SKILL.md`

---

## Rules

- Always create skills under `skillsBuilder/claude_301/skills/`, never under `.claude/skills/` (those are project-local, not plugin skills)
- Skill directory names must be kebab-case. **Skill names cannot contain underscores (`_`)** — use hyphens (`-`) only
- The generated SKILL.md must always include YAML frontmatter with `name` and `description` fields
- The `description` in frontmatter must include trigger phrases (e.g., "Use when the user says...") — this is how Claude Code matches skills to user intent
- Do not create `scripts/`, `resources/`, or `templates/` subdirectories unless the user specifically requests them
- Keep the scaffold minimal but complete — the right structure with meaningful placeholders, not filler content

---

## Reference Skills

Good examples to consult when writing skill content:
- `.claude/skills/writeback/SKILL.md` (concise project-local skill)
- `.claude/skills/generate/SKILL.md` (complex skill with subagents)
