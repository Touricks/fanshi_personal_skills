---
name: rule-creator
description: >
  Create a new .claude/rules/*.md rule file with proper structure and conditional
  paths frontmatter when appropriate. ALWAYS use this skill when the user says
  "create a rule", "add a rule", "new rule", "new rule for...", "write a rule",
  "add instruction", "create instruction", or wants to add a .claude/rules/ file.
  This skill guides the agent to determine whether the rule applies globally or
  only to specific file types/paths, generates the correct frontmatter, and
  updates README.md afterward. Do NOT create .claude/rules/ files without
  invoking this skill first.
---

# Create Rule

Create well-structured `.claude/rules/*.md` files with correct conditional loading via `paths` frontmatter.

## Why This Skill Exists

Claude Code loads rules from `.claude/rules/` in two modes:
- **Global rules** (no `paths` frontmatter): loaded unconditionally at session start, active for every conversation turn.
- **Conditional rules** (`paths` frontmatter present): loaded only when the model reads a file whose path matches the glob patterns.

Getting the scope wrong wastes tokens (global rule that only matters for `.tf` files) or silently fails (conditional rule with a broken glob). This skill ensures every rule is intentionally scoped.

---

## Workflow

### Step 1: Determine scope — global or conditional

This is the critical decision. Ask the user (or infer from context):

> "Does this rule apply to ALL files in the project, or only to SPECIFIC file types or paths?"

**Decision tree:**

| Signal in the rule content | Scope | Action |
|----------------------------|-------|--------|
| Mentions a specific language or framework | Conditional | e.g., "When writing Terraform..." -> `paths: "*.tf"` |
| Mentions specific file extensions | Conditional | e.g., "For test files..." -> `paths: "*.test.{ts,tsx}"` |
| Mentions a specific directory | Conditional | e.g., "In the API routes..." -> `paths: "src/api/**"` |
| General coding style or conventions | Global | e.g., "Always use descriptive variable names" |
| Project workflow or process | Global | e.g., "Run tests before committing" |
| Security practices | Global | e.g., "Never commit secrets" |

If the user's intent is ambiguous, ask — do NOT default to global. Conditional rules keep sessions lean.

### Step 2: Determine the filename

Use kebab-case, descriptive, and short:

```
.claude/rules/{topic-slug}.md
```

Examples: `terraform-naming.md`, `test-structure.md`, `api-error-handling.md`

Check if `.claude/rules/{filename}` already exists. If yes, ask whether to overwrite or pick a different name.

### Step 3: Generate the rule file

**If GLOBAL (no paths frontmatter):**

Write plain markdown with no frontmatter at all. Do NOT add empty frontmatter (`---\n---`).

```markdown
Rule content here — plain markdown, concise and actionable.
```

**If CONDITIONAL (with paths frontmatter):**

Add YAML frontmatter with a `paths` field. Valid formats:

Single pattern:
```markdown
---
paths: "*.tf"
---

Terraform resources must include a tags block.
```

Multiple patterns as YAML list:
```markdown
---
paths:
  - "*.tf"
  - "*.tfvars"
---

All variable definitions must include a description field.
```

Brace expansion:
```markdown
---
paths: "*.{ts,tsx}"
---

React components must use named exports.
```

Directory-scoped:
```markdown
---
paths: ["src/api/**"]
---

API route handlers must validate request body before processing.
```

#### Valid `paths` pattern syntax

The `paths` field uses `.gitignore`-style glob patterns (powered by the `ignore` npm package):

| Format | Example | Matches |
|--------|---------|---------|
| Single string | `paths: "*.tf"` | All `.tf` files anywhere |
| YAML list | `paths:\n  - "*.tf"\n  - "*.tfvars"` | Both patterns |
| Brace expansion | `paths: "*.{ts,tsx}"` | `.ts` and `.tsx` files |
| Directory glob | `paths: "src/api/**"` | Everything under `src/api/` |
| Comma-separated string | `paths: "*.tf, *.tfvars"` | Both patterns |

Note: `src/api` and `src/api/**` are equivalent — Claude Code's parser strips the `/**` suffix because the `ignore` library already matches both the path and everything inside it.

Note: If all patterns resolve to `**` (match-all), Claude Code treats the rule as unconditional — same as having no `paths` field.

### Step 4: Consider subdirectory organization

`.claude/rules/` supports recursive subdirectory loading. When the project already has many rules, or the new rule belongs to a clear domain, organize into subdirectories:

```
.claude/rules/
  frontend/
    react-standards.md
    css-conventions.md
  backend/
    api-design.md
    database.md
  infra/
    terraform-naming.md    # paths: "*.tf"
```

**When to use subdirectories:**
- 5+ rule files already exist — time to group
- Rule clearly belongs to an existing domain subdirectory
- Multiple teams maintain separate rule sets

**When flat is fine:**
- Fewer than 5 rules total
- Rule is cross-cutting (e.g., `commit-messages.md`)

Both conditional and global rules work identically in subdirectories — the `paths` frontmatter behavior does not change.

### Step 5: Write the file

1. Ensure the directory exists: `mkdir -p .claude/rules/` (or `mkdir -p .claude/rules/{subdirectory}/`)
2. Write the rule file
3. Verify the file was created

### Step 6: Confirm

Report to the user:
- Created: `.claude/rules/{filename}` (or `.claude/rules/{subdir}/{filename}`)
- Scope: Global (loads every session) or Conditional (loads when reading files matching `{patterns}`)

---

## Rules

- ALWAYS determine scope (global vs. conditional) before writing the file. Never skip Step 1.
- One rule per file. If the user wants multiple rules, create separate files.
- Rule filenames must be kebab-case — no underscores.
- Global rules need NO frontmatter. Do not add empty frontmatter to global rules.
- Conditional rules MUST have `paths` in YAML frontmatter. The `paths` field is the ONLY frontmatter field that Claude Code's rule loading system reads for conditional activation.
- Do NOT use `name` or `description` frontmatter fields in rule files — those are for SKILL.md, not rules.
- Keep rule content concise and actionable — one topic per file.

## How Claude Code Loads Rules (Source Reference)

Understanding the internals helps write correct `paths` patterns.

**Frontmatter parsing** — `parseFrontmatterPaths()` extracts and normalizes glob patterns:

```typescript
function parseFrontmatterPaths(rawContent: string): {
  content: string; paths?: string[]
} {
  const { frontmatter, content } = parseFrontmatter(rawContent)
  if (!frontmatter.paths) {
    return { content }  // No paths → unconditional (global) rule
  }
  const patterns = splitPathInFrontmatter(frontmatter.paths)
    .map(pattern => pattern.endsWith('/**') ? pattern.slice(0, -3) : pattern)
    .filter((p: string) => p.length > 0)
  // If all patterns are ** (match-all), treat as unconditional
  if (patterns.length === 0 || patterns.every((p: string) => p === '**')) {
    return { content }
  }
  return { content, paths: patterns }
}
```

**Rule file discovery** — `processMdRules()` recursively reads `.md` files and splits them by scope:

```typescript
// Inside processMdRules(), for each .md file found:
if (isFile && entry.name.endsWith('.md')) {
  const files = await processMemoryFile(resolvedEntryPath, type, processedPaths, includeExternal)
  result.push(
    ...files.filter(f => (conditionalRule ? f.globs : !f.globs)),
  )
}
```

The same directory is scanned twice: once with `conditionalRule: false` (session start — collects files without `globs`), once with `conditionalRule: true` (on file read — collects files with `globs`).

**Conditional rule matching** — `processConditionedMdRules()` checks glob patterns against target file:

```typescript
return conditionedRuleMdFiles.filter(file => {
  const baseDir = type === 'Project'
    ? dirname(dirname(rulesDir))  // Parent of .claude/
    : getOriginalCwd()
  const relativePath = isAbsolute(targetPath)
    ? relative(baseDir, targetPath) : targetPath
  return ignore().add(file.globs).ignores(relativePath)
})
```

Key detail: For project rules, glob patterns are resolved relative to the directory containing `.claude/`, not relative to the rule file itself.
