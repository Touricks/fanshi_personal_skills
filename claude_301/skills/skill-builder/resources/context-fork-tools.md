# Skill Execution Context and Tool Permissions

Configure how a skill runs and what it can access. This skill covers two SKILL.md frontmatter features that control execution boundaries: `context` (where the skill runs) and `allowed-tools` (what the skill can use). These are independent settings — you can use either or both.

---

## Part 1: How Skills Execute — Inline vs Fork

By default, skills run **inline**: the skill's markdown content expands directly into the current conversation as if the user had typed it. All tool calls, intermediate reasoning, and outputs stay in the main context window.

The alternative is **fork**: the skill runs in an isolated sub-agent with its own token budget. Only the final result returns to the main conversation — all intermediate work is discarded.

The frontmatter field that controls this:

```yaml
# frontmatterParser.ts:40-43
context?: 'inline' | 'fork' | null
# 'inline' = skill content expands into the current conversation (default)
# 'fork'   = skill runs in a sub-agent with separate context and token budget
```

Source: `reference/src/utils/frontmatterParser.ts:40-43`

The parsing is straightforward — anything other than `'fork'` resolves to inline:

```typescript
// loadSkillsDir.ts:260
executionContext: frontmatter.context === 'fork' ? 'fork' : undefined
```

---

## Part 2: When to Use `context: fork`

The decision is about **output volume and self-containment**, not complexity.

### Use `context: fork` when:

- **Large intermediate output**: The skill scans many files, analyzes logs, or explores alternatives — producing KB-level intermediate text that would overwhelm the main context
- **Exploration tasks**: Codebase architecture analysis, dependency audits, multi-option brainstorming — tasks where the journey matters less than the destination
- **Self-contained workflow**: The skill runs start-to-finish without needing mid-process user input
- **Context protection**: You want to guarantee the skill cannot exhaust the main conversation's context window

### Stay inline when:

- **Short output**: A code formatting or simple generation skill produces only the final artifact
- **User interaction needed**: The skill might ask clarifying questions mid-execution
- **Conversation continuity**: The skill's intermediate findings are useful for subsequent turns (e.g., a skill that discovers patterns the user wants to discuss)
- **Simple operations**: 2-3 tool calls with predictable output size

### Rule of thumb

If you'd be comfortable with the skill's entire execution trace pasted into the conversation, stay inline. If that trace would be 50+ lines of intermediate work that nobody needs to see, fork it.

---

## Part 3: Fork Mechanics — What Actually Happens

When the SkillTool encounters a forked skill, it takes a completely different execution path:

```typescript
// SkillTool.ts:622-632
if (command?.type === 'prompt' && command.context === 'fork') {
  return executeForkedSkill(
    command, commandName, args, context,
    canUseTool, parentMessage, onProgress,
  )
}
```

The `executeForkedSkill()` function (SkillTool.ts:122-212) does the following:

1. **Creates a unique agent ID** — `createAgentId()` gives the sub-agent its own identity
2. **Prepares isolated context** — `prepareForkedCommandContext()` (forkedAgent.ts:191-232):
   - Loads full skill content with `$ARGUMENTS` substituted via `getPromptForCommand(args)`
   - Parses `allowed-tools` and creates a modified `getAppState` that injects them into permissions
   - Selects the agent type from `command.agent` (defaults to `'general-purpose'`)
   - Wraps skill content into a user-message prompt for the sub-agent
3. **Runs the sub-agent** — `runAgent()` executes with the isolated context and its own API call budget
4. **Extracts the result** — `extractResultText()` walks the sub-agent's messages to find the final assistant output
5. **Returns only the summary** — the main conversation receives a structured result with `status: 'forked'` and the extracted text

Key architectural insight: the sub-agent's intermediate messages (tool calls, reasoning steps, exploration output) are collected in a local `agentMessages` array and **never enter the main context window**. This is the core mechanism that protects the parent conversation.

---

## Part 4: The `agent` Frontmatter Field

An optional companion to `context: fork` that selects which agent type runs the sub-agent:

```yaml
context: fork
agent: general-purpose   # default if omitted
```

Source: `reference/src/utils/frontmatterParser.ts:44-46`

```typescript
// 'agent' field type definition
agent?: string | null
// Agent type to use when forked (e.g., 'Bash', 'general-purpose')
// Only applicable when context is 'fork'
```

The agent field is resolved during fork preparation:

```typescript
// forkedAgent.ts:212-217 (approximate)
const agentType = command.agent ?? 'general-purpose'
```

When to override the default:
- Use a specific agent type when the skill is heavily oriented toward one tool (e.g., a shell-heavy skill might benefit from an agent optimized for Bash)
- Leave as default (`'general-purpose'`) for most skills — it handles diverse tool usage well
- The `agent` field is ignored entirely when `context` is `inline`

---

## Part 5: `allowed-tools` — Least-Privilege Permissions

`allowed-tools` restricts which tools a skill can use. It works in **both** inline and fork mode, but the mechanism differs slightly.

### How it works

The frontmatter value is parsed by `parseSlashCommandToolsFromFrontmatter()` (markdownConfigLoader.ts:132-140), which returns a string array of tool patterns.

At runtime, these patterns are injected into the permission context via `getAppState()` modification:

```typescript
// SkillTool.ts:779-806 (inline mode)
if (allowedTools.length > 0) {
  const previousGetAppState = modifiedContext.getAppState
  modifiedContext = {
    ...modifiedContext,
    getAppState() {
      const appState = previousGetAppState()
      return {
        ...appState,
        toolPermissionContext: {
          ...appState.toolPermissionContext,
          alwaysAllowRules: {
            ...appState.toolPermissionContext.alwaysAllowRules,
            command: [
              ...new Set([
                ...(appState.toolPermissionContext.alwaysAllowRules.command || []),
                ...allowedTools,
              ]),
            ],
          },
        },
      }
    },
  }
}
```

### Critical: `allowed-tools` behaves differently in inline vs fork mode

**Inline mode** — `allowed-tools` is a **permission grant**, not a filter. It auto-approves the listed tools so the user is not prompted. The skill can still attempt to call unlisted tools, and the user will see a permission prompt for those.

**Fork mode** — `allowed-tools` is effectively a **filter**. Because forked skills run with `shouldAvoidPermissionPrompts: true` (set by `createSubagentContext` at forkedAgent.ts:356-374), unlisted tools that would normally trigger a permission prompt are **silently denied** — there is no interactive UI to prompt the user. This means only tools in `allowed-tools` (plus any pre-existing auto-allow rules) will actually work in a fork.

```typescript
// forkedAgent.ts:356-374 — fork sets shouldAvoidPermissionPrompts
const getAppState = overrides?.shareAbortController
  ? parentContext.getAppState
  : () => {
      const state = parentContext.getAppState()
      return {
        ...state,
        toolPermissionContext: {
          ...state.toolPermissionContext,
          shouldAvoidPermissionPrompts: true,  // ← silent deny for unlisted tools
        },
      }
    }
```

**Practical implication**: When designing a forked skill, your `allowed-tools` list must be **complete** — any tool you forget to list will silently fail. For inline skills, a missing tool just triggers a permission prompt.

For forked skills, the tool injection goes through `createGetAppStateWithAllowedTools()` (forkedAgent.ts:146-170), which wraps the base `getAppState` before passing it to `runAgent()`.

---

## Part 6: Tool String Syntax

### YAML formats

Both formats are equivalent:

```yaml
# Inline string (comma-separated)
allowed-tools: Read, Grep, Glob, Bash(npm:*)

# YAML list
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm:*)
```

### Pattern syntax

The parser (`parseToolListFromCLI` in permissionSetup.ts:813-870) is **paren-aware**: commas and spaces inside parentheses are preserved as part of the tool pattern.

Examples:
- `Read` — grants all Read operations
- `Bash(npm:*)` — grants Bash only for `npm` commands
- `Bash(gh:*)` — grants Bash only for `gh` commands
- `Bash(ls:*, wc:*, find:*)` — grants Bash for multiple specific commands

The parsing logic:
```
"Bash(gh:*), Glob"       → ['Bash(gh:*)', 'Glob']        # comma outside parens
"Bash(gh:*) Glob"        → ['Bash(gh:*)', 'Glob']        # space outside parens
"Bash(ls:*, wc:*), Glob" → ['Bash(ls:*, wc:*)', 'Glob']  # comma inside parens preserved
```

---

## Part 7: Design Patterns

### Pattern A: Read-Only Exploration (fork + restricted tools)

For skills that scan the codebase and produce a summary:

```yaml
---
name: architecture-scan
description: Scan codebase architecture and return a summary
context: fork
allowed-tools:
  - Read
  - Grep
  - Glob
---
```

Why fork: produces large intermediate output during exploration.
Why these tools: read-only operations — the skill cannot modify any files.

### Pattern B: Code Generation (inline + edit tools)

For skills that generate or modify code interactively:

```yaml
---
name: api-scaffold
description: Generate API endpoint boilerplate
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash(npm:*, npx:*)
---
```

Why inline: output is the code itself, which stays in conversation for follow-up discussion.
Why these tools: needs to read existing code, write new files, and run scaffolding commands.

### Pattern C: Self-Contained Analysis (fork + specific agent)

For skills that run a focused analysis pipeline:

```yaml
---
name: dependency-audit
description: Audit all dependencies for known vulnerabilities
context: fork
agent: general-purpose
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm:audit, yarn:audit)
---
```

### Anti-pattern: Fork + User Interaction

Forked skills cannot use `AskUserQuestion` in practice. The mechanism is not an explicit blocklist — rather, `createSubagentContext` (forkedAgent.ts:356-374) removes the UI callbacks (`setToolJSX`, `addNotification`, `openMessageSelector`) that AskUserQuestion needs to display its prompt, and sets `shouldAvoidPermissionPrompts: true`. Even if AskUserQuestion were auto-allowed, it would fail because the UI layer is absent. If your skill needs to ask the user clarifying questions mid-execution, it must run inline.

---

## Quick Reference Checklist

When designing a new skill's execution context:

- [ ] Will the skill produce large intermediate output? → Consider `context: fork`
- [ ] Does the skill need mid-execution user input? → Must use inline (no fork)
- [ ] What's the minimum tool set needed? → List in `allowed-tools`
- [ ] Does the skill only read files? → Restrict to `Read, Grep, Glob`
- [ ] Does the skill run shell commands? → Use specific patterns like `Bash(npm:*)`
- [ ] Is the skill heavily shell-oriented? → Consider setting `agent` field
- [ ] Could the skill accidentally modify code? → Omit `Edit`, `Write` from `allowed-tools`

---

## Frontmatter Fields Not Covered Here

These SKILL.md frontmatter fields exist but are outside this skill's scope:

| Field | Purpose | Priority |
|-------|---------|----------|
| `model` | Override model for skill execution (e.g., `haiku`, `opus`, `inherit`) | High — affects cost/quality tradeoff |
| `effort` | Set reasoning effort level for forked agent | High — merged into agent definition |
| `hooks` | Register PreToolUse/PostToolUse hooks during skill execution | Medium — powerful but rare |
| `user-invocable` | Control whether users can type `/skill-name` (default differs by directory) | Medium |
| `when_to_use` | Guide model's proactive invocation decisions | Medium — primary discoverability mechanism |
| `paths` | Glob patterns for file-scoped activation | Low-medium |
| `argument-hint` | CLI completion hint for arguments | Covered by **argument-hint-routing** |

---

## See Also

- **argument-hint-routing** — for designing how skills receive and route arguments
- **agent-tool-allocation** — for agent-level tool boundaries (broader scope than skill-level `allowed-tools`)
- **create-skill-template** — for scaffolding new skills with proper directory structure
