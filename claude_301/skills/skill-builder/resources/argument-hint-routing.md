# Skill Argument Handling: Hints, Substitution, and Routing

Design skills that accept user input through arguments and adapt their behavior accordingly. This skill covers the full argument pipeline: how arguments reach a skill, how they're parsed and substituted into content, how to write effective hints, and how to build multi-mode skills that route behavior based on what the user provides.

---

## Part 1: How Skills Receive Arguments

When a user types `/skill-name arg1 arg2` or the model invokes `Skill("skill-name", "arg1 arg2")`, everything after the skill name becomes the `args` string. This string flows through a pipeline:

1. **Invocation** — user or model provides args
2. **`getPromptForCommand(args, context)`** — called in `loadSkillsDir.ts:344-358`
3. **`substituteArguments(content, args, true, argumentNames)`** — replaces placeholders in the SKILL.md body
4. **Final content** — sent to the model (inline) or sub-agent (fork)

The key function is `substituteArguments()` in `argumentSubstitution.ts:94-145`. It handles four distinct placeholder patterns, applied in a specific order to avoid conflicts.

If no placeholders exist in the skill content and args are non-empty, the fallback behavior appends `\n\nARGUMENTS: {args}` to the end of the content.

---

## Part 2: The Four Substitution Patterns

Source: `reference/src/utils/argumentSubstitution.ts:94-145`

Substitution happens in this exact order (order matters to prevent conflicts):

### Pattern 1: Named Arguments — `$name`

```typescript
// argumentSubstitution.ts:109-121
// Match $name but not $name[...] or $nameXxx (word chars)
content = content.replace(
  new RegExp(`\\$${name}(?![\\[\\w])`, 'g'),
  parsedArgs[i] ?? '',
)
```

Requires the `arguments` frontmatter field to define names. Named arguments map positionally: `arguments: source target` means `$source` = first arg, `$target` = second arg.

### Pattern 2: Indexed Arguments — `$ARGUMENTS[N]`

```typescript
// argumentSubstitution.ts:123-127
content = content.replace(/\$ARGUMENTS\[(\d+)\]/g, (_, indexStr) => {
  const index = parseInt(indexStr, 10)
  return parsedArgs[index] ?? ''
})
```

Zero-based indexing. `$ARGUMENTS[0]` is the first argument, `$ARGUMENTS[1]` is the second.

### Pattern 3: Shorthand Indexing — `$N`

```typescript
// argumentSubstitution.ts:129-133
content = content.replace(/\$(\d+)(?!\w)/g, (_, indexStr) => {
  const index = parseInt(indexStr, 10)
  return parsedArgs[index] ?? ''
})
```

`$0` is equivalent to `$ARGUMENTS[0]`. The `(?!\w)` lookahead prevents matching `$0abc` or `$00`.

### Pattern 4: Full Arguments — `$ARGUMENTS`

```typescript
// argumentSubstitution.ts:135-136
content = content.replaceAll('$ARGUMENTS', args)
```

Replaced **last** so that `$ARGUMENTS[0]` is handled before `$ARGUMENTS` consumes it.

### Why order matters

The substitution chain is: named → indexed → shorthand → full. This prevents:
- `$ARGUMENTS` from consuming `$ARGUMENTS[0]` (indexed runs first)
- `$0` from matching inside `$00` (regex lookahead handles this)
- Named args from clashing with indexed notation (named runs first and uses word-boundary matching)

---

## Part 3: Defining Named Arguments

The `arguments` frontmatter field declares named argument placeholders:

```yaml
# String format (space-separated)
arguments: sourceFile targetFile format

# Array format
arguments:
  - sourceFile
  - targetFile
  - format
```

Parsing is handled by `parseArgumentNames()` (argumentSubstitution.ts:50-68):

```typescript
export function parseArgumentNames(
  argumentNames: string | string[] | undefined,
): string[] {
  // Filter out empty strings and numeric-only names
  const isValidName = (name: string): boolean =>
    typeof name === 'string' && name.trim() !== '' && !/^\d+$/.test(name)

  if (Array.isArray(argumentNames)) {
    return argumentNames.filter(isValidName)
  }
  if (typeof argumentNames === 'string') {
    return argumentNames.split(/\s+/).filter(isValidName)
  }
  return []
}
```

Validation rules:
- **Numeric-only names are rejected** — `arguments: 0 1 2` would produce an empty list because `'0'`, `'1'`, `'2'` match `/^\d+$/` and conflict with the `$0`, `$1` shorthand pattern
- **Empty strings are filtered** — extra whitespace in the string format is safe
- **Names are positional** — `arguments: source target` means the first user argument maps to `$source`, the second to `$target`

---

## Part 4: Writing Effective `argument-hint` Strings

`argument-hint` is displayed in the CLI as gray placeholder text after the command name, guiding users on what to type.

```yaml
argument-hint: "<file-path> [output-format]"
```

Source: `reference/src/skills/loadSkillsDir.ts:245-248`

```typescript
argumentHint:
  frontmatter['argument-hint'] != null
    ? String(frontmatter['argument-hint'])
    : undefined,
```

### Conventions from built-in skills

Established patterns in Claude Code's bundled skills:

| Skill | Hint | Pattern |
|-------|------|---------|
| loop | `[interval] <prompt>` | Optional interval, required prompt |
| batch | `<instruction>` | Single required arg |
| debug | `[issue description]` | Single optional arg |

The convention:
- **`<angle-brackets>`** = required argument
- **`[square-brackets]`** = optional argument
- Descriptive names that indicate expected content type

### Best practices

- **Keep hints short** — they share horizontal space with the skill name in the CLI
- **Match hint names to `arguments` field names** — `argument-hint: "<source> <target>"` with `arguments: source target` creates consistency
- **Don't put examples in the hint** — the hint is for structure, the description is for examples
- **Use content-type cues** — `<file-path>`, `<module-name>`, `<PR-number>` help users understand what to provide

---

## Part 5: Progressive Argument Hints

When `arguments` (named args) are defined, the CLI can dynamically update the hint as the user types, showing only remaining unfilled arguments.

Source: `reference/src/utils/argumentSubstitution.ts:76-83`

```typescript
export function generateProgressiveArgumentHint(
  argNames: string[],
  typedArgs: string[],
): string | undefined {
  const remaining = argNames.slice(typedArgs.length)
  if (remaining.length === 0) return undefined
  return remaining.map(name => `[${name}]`).join(' ')
}
```

Example with `arguments: source target format`:
- User types nothing → hint shows `[source] [target] [format]`
- User types `foo.ts` → hint shows `[target] [format]`
- User types `foo.ts bar.ts` → hint shows `[format]`
- User types `foo.ts bar.ts json` → hint disappears (all filled)

Progressive hints require the `arguments` field — they cannot work with bare `argument-hint` alone because the system needs to know how many named arguments exist to track which are filled.

---

## Part 6: Designing Multi-Mode Skills

Arguments enable a single skill to behave differently based on what the user provides. Three common patterns:

### Pattern A: Template Selection

The first argument selects which behavior path to follow:

```yaml
---
name: scaffold
description: Generate boilerplate for different frameworks
arguments: framework component
argument-hint: "<framework> <component-name>"
---

# Scaffold Generator

Generate a $framework component named $component.

## Framework-Specific Instructions

If the framework is **react**: create a functional component with hooks...
If the framework is **vue**: create a single-file component with setup script...
If the framework is **svelte**: create a .svelte file with script and markup...
```

Usage: `/scaffold react UserProfile` → `$framework` = "react", `$component` = "UserProfile"

### Pattern B: Mode Switching via Argument Presence

The skill detects whether arguments were provided and adapts:

```yaml
---
name: analyze
description: Analyze code quality (interactive or targeted)
argument-hint: "[file-or-directory]"
---

# Code Analysis

Analyze $ARGUMENTS for code quality issues.

If no arguments were provided (ARGUMENTS section is empty), ask the user
which files or directories to analyze. If arguments are present, proceed
directly with analysis on the specified path.
```

Usage:
- `/analyze` → no args, enters interactive mode
- `/analyze src/auth/` → targets the auth directory directly

This pattern works because when `args` is undefined (no arguments), `$ARGUMENTS` is not substituted and the original placeholder text remains. The model reads the conditional instructions and adapts.

### Pattern C: Free-Form with Structured Prefix

Use `$ARGUMENTS` for the full input when the skill accepts natural-language instructions:

```yaml
---
name: review
description: Review code with a specific focus area
argument-hint: "<focus-area> [additional-context]"
---

# Focused Code Review

Review the current changes with this specific focus:

$ARGUMENTS

Apply the review criteria relevant to the stated focus area.
```

Usage: `/review security Check for SQL injection in the new API endpoints`

---

## Part 7: Argument Parsing Details and Pitfalls

### How arguments are parsed

Arguments are parsed using shell-quote rules via `parseArguments()` (argumentSubstitution.ts:24-39):

```typescript
export function parseArguments(args: string): string[] {
  if (!args || !args.trim()) return []

  const result = tryParseShellCommand(args, key => `$${key}`)
  if (!result.success) {
    return args.split(/\s+/).filter(Boolean)  // fallback: whitespace split
  }
  return result.tokens.filter(
    (token): token is string => typeof token === 'string',
  )
}
```

This means:
- `"hello world"` is **one** argument (quoted string preserved)
- `foo bar baz` is **three** arguments
- Shell operators are filtered out — only string tokens survive
- `$KEY` syntax is preserved literally (not expanded by the shell parser)

### Common pitfalls

**Pitfall 1: `undefined` vs empty string**
- `args === undefined` (skill invoked without arguments) → **no substitution at all**, content returned unchanged with placeholders intact
- `args === ''` (empty string) → substitution runs, replacing all placeholders with empty strings
- This distinction is intentional: model-invoked skills without args should see the original template

**Pitfall 2: Auto-append when no placeholders exist**
If your skill body contains no `$ARGUMENTS`, `$0`, or `$name` placeholders, non-empty args are automatically appended as `\n\nARGUMENTS: {args}`. This can be unexpected if you forget to add placeholders.

```typescript
// argumentSubstitution.ts:140-142
if (content === originalContent && appendIfNoPlaceholder && args) {
  content = content + `\n\nARGUMENTS: ${args}`
}
```

**Pitfall 3: Numeric argument names**
`arguments: 0 1 2` produces an empty list because `parseArgumentNames()` rejects numeric-only names — they conflict with the `$0`, `$1` shorthand pattern.

**Pitfall 4: Named arg word-boundary matching**
`$source` will NOT match inside `$sourceFile` due to the regex lookahead `(?![\[\w])`. Choose distinct names that don't share prefixes, or use the longer name first in the `arguments` field.

---

## Quick Reference Checklist

When designing argument handling for a skill:

- [ ] Does the skill need arguments at all? → If not, skip `argument-hint` and `arguments`
- [ ] How many distinct inputs does the skill need? → Define in `arguments` field
- [ ] Are arguments optional or required? → Reflect in `argument-hint` with `[]` vs `<>`
- [ ] Does the skill have multiple modes? → Use first argument as mode selector
- [ ] Do argument names share prefixes? → Rename to avoid word-boundary conflicts
- [ ] Is `$ARGUMENTS` used alongside indexed args? → Safe, but verify substitution order
- [ ] Does the skill work without arguments? → Test the `undefined` args path

---

## Fork + Arguments Interaction

When a skill runs with `context: fork`, the substituted content becomes the **sole user message** to the sub-agent (via `createUserMessage({ content: skillContent })` in `prepareForkedCommandContext` at forkedAgent.ts:224). This has important implications for argument design:

- **Arguments must be self-contained** — the sub-agent has no prior conversation context. If your skill uses `$ARGUMENTS` to reference something the user said earlier, the fork won't have that context.
- **Auto-append is more prominent** — the fallback `\n\nARGUMENTS: {args}` append becomes part of the only message the sub-agent sees, making it more influential than in inline mode where it's one message among many.
- **Undefined args in forks** — if `args` is undefined, the fork receives the raw template with `$ARGUMENTS` placeholders intact. The sub-agent may interpret these literally, leading to confusing behavior. For forked skills, always validate that arguments are provided or handle the no-args case explicitly.

---

## Frontmatter Fields Not Covered Here

These SKILL.md frontmatter fields exist but are outside this skill's scope:

| Field | Purpose | Priority |
|-------|---------|----------|
| `model` | Override model for skill execution | High |
| `effort` | Set reasoning effort level | High |
| `context` | Execution isolation (`inline` vs `fork`) | Covered by **context-fork-tools** |
| `allowed-tools` | Tool permission scoping | Covered by **context-fork-tools** |
| `hooks` | Register event hooks during execution | Medium |
| `user-invocable` | Control `/slash` command visibility | Medium |
| `when_to_use` | Guide model's proactive invocation | Medium |

---

## See Also

- **context-fork-tools** — for deciding skill execution mode and tool permissions
- **create-skill-template** — for scaffolding new skills with argument support
