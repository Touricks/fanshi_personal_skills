---
name: agent-tool-allocation
description: >
  Guide for assigning tools to agents and configuring `tool_choice` in
  multi-agent systems. Covers allowlists/blocklists (`tools` vs
  `disallowedTools`), wildcard expansion, `filterToolsForAgent`, built-in agent
  scoping, ToolSelector buckets, `tool_choice` modes (auto, any, forced), and
  agent schemas with `lazySchema` and `BuiltInAgentDefinition`. Use when the user
  says "agent tool allocation", "tool allocation", "tool_choice", "which tools
  for which agent", "agent tool scoping", "allowlist blocklist",
  "filterToolsForAgent", "disallowedTools", "lazySchema",
  "BuiltInAgentDefinition", "ASYNC_AGENT_ALLOWED_TOOLS",
  "COORDINATOR_MODE_ALLOWED_TOOLS", or "agent tool boundaries"; also use when
  designing a new agent's tool access. For tool descriptions use
  `mcp-tool-design`; for errors use `mcp-error-response`; for MCP optimization
  use `mcp-tool-enhancement`.
---

# Agent Tool Allocation: Boundaries, Scoping, and tool_choice

How to decide which tools each agent can access, and how to control which tool the model calls on a given turn. Tool allocation determines what an agent *can* use; `tool_choice` determines what the model *must* use on a specific API call. These are related but distinct design decisions, and getting them right is the difference between a reliable multi-agent system and one that misfires.

In Claude Code, every agent — built-in, custom, or plugin — declares its tool boundaries through a combination of allowlists, blocklists, and runtime filtering. The source code in `reference/src/` provides concrete examples of each strategy.

---

## Part 1: The Allowlist / Blocklist Model

Every agent definition has two optional fields that control tool access. Understanding when to use each is fundamental to agent design.

### 1.1 `tools` — The Positive Allowlist

The `tools` field is an array of tool name strings. When specified with concrete names, the agent can **only** use those tools — everything else is invisible to it.

```typescript
// reference/src/tools/AgentTool/built-in/statuslineSetup.ts:134-144
export const STATUSLINE_SETUP_AGENT: BuiltInAgentDefinition = {
  agentType: 'statusline-setup',
  tools: ['Read', 'Edit'],  // Only 2 tools — nothing else
  // ...
}
```

This is the safest strategy: the agent sees exactly what you intend and nothing more.

### 1.2 `disallowedTools` — The Negative Blocklist

The `disallowedTools` field lists tools to **exclude**. The agent gets all available tools minus those in the blocklist.

```typescript
// reference/src/tools/AgentTool/built-in/exploreAgent.ts:64-73
export const EXPLORE_AGENT: BuiltInAgentDefinition = {
  agentType: 'Explore',
  disallowedTools: [
    AGENT_TOOL_NAME,          // No spawning sub-agents
    EXIT_PLAN_MODE_TOOL_NAME, // No plan mode control
    FILE_EDIT_TOOL_NAME,      // No editing files
    FILE_WRITE_TOOL_NAME,     // No writing files
    NOTEBOOK_EDIT_TOOL_NAME,  // No notebook edits
  ],
  // ...
}
```

The Explore agent needs many read tools (Glob, Grep, Read, WebFetch, WebSearch) but must not modify anything. Rather than listing every read tool (fragile — new read tools would be excluded), it blocks the destructive ones and inherits everything else.

### 1.3 The Wildcard `['*']` and `undefined`

Both `tools: ['*']` and omitting `tools` entirely resolve to "all available tools (after filtering)":

```typescript
// reference/src/tools/AgentTool/agentToolUtils.ts:162-165
const hasWildcard =
  agentTools === undefined ||
  (agentTools.length === 1 && agentTools[0] === '*')
```

The General Purpose agent uses `tools: ['*']` explicitly to signal intent — it needs broad access:

```typescript
// reference/src/tools/AgentTool/built-in/generalPurposeAgent.ts:25-29
export const GENERAL_PURPOSE_AGENT: BuiltInAgentDefinition = {
  agentType: 'general-purpose',
  tools: ['*'],
  // ...
}
```

The wildcard does **not** bypass runtime filtering — `ALL_AGENT_DISALLOWED_TOOLS` still applies.

### 1.4 Decision Rule: When to Use Allowlist vs Blocklist

| Strategy | When to use | Trade-off |
|----------|------------|-----------|
| **Allowlist** (`tools: ['Read', 'Edit']`) | Narrow, well-defined purpose; agent needs 2-5 specific tools | Safest, but requires update when new tools are relevant |
| **Blocklist** (`disallowedTools: [...]`) | Broad access needed but specific tools must be excluded | Self-maintains as new tools arrive, but new dangerous tools could leak through |
| **Wildcard** (`tools: ['*']`) | General-purpose agent that should access everything available | Maximum flexibility, relies entirely on runtime filtering for safety |

**Rule of thumb**: if you can name every tool the agent needs, use an allowlist. If you can only name what it must *not* have, use a blocklist.

---

## Part 2: Multi-Layer Tool Filtering

An agent's declared tools are just the starting point. The runtime applies several additional filtering layers before the model sees any tools.

### 2.1 The Filtering Pipeline: `filterToolsForAgent()`

Every tool passes through `filterToolsForAgent()` before reaching any agent. The function applies filters in order — a tool must survive all layers:

```typescript
// reference/src/tools/AgentTool/agentToolUtils.ts:70-116
export function filterToolsForAgent({
  tools, isBuiltIn, isAsync = false, permissionMode,
}: { ... }): Tools {
  return tools.filter(tool => {
    // Layer 1: MCP tools always pass through
    if (tool.name.startsWith('mcp__')) { return true }

    // Layer 2: Global blocklist — no agent gets these
    if (ALL_AGENT_DISALLOWED_TOOLS.has(tool.name)) { return false }

    // Layer 3: Custom agent restrictions (superset of global)
    if (!isBuiltIn && CUSTOM_AGENT_DISALLOWED_TOOLS.has(tool.name)) { return false }

    // Layer 4: Async agents limited to allowlist
    if (isAsync && !ASYNC_AGENT_ALLOWED_TOOLS.has(tool.name)) {
      // Layer 5: Teammate exception — coordination tools
      if (isAgentSwarmsEnabled() && isInProcessTeammate()) {
        if (toolMatchesName(tool, AGENT_TOOL_NAME)) { return true }
        if (IN_PROCESS_TEAMMATE_ALLOWED_TOOLS.has(tool.name)) { return true }
      }
      return false
    }
    return true
  })
}
```

### 2.2 Global Blocklists: `ALL_AGENT_DISALLOWED_TOOLS`

Some tools are dangerous in any agent context — they enable recursion, break thread boundaries, or expose main-thread-only abstractions:

```typescript
// reference/src/constants/tools.ts:36-46
export const ALL_AGENT_DISALLOWED_TOOLS = new Set([
  TASK_OUTPUT_TOOL_NAME,       // Prevents recursion
  EXIT_PLAN_MODE_V2_TOOL_NAME, // Plan mode is main-thread only
  ENTER_PLAN_MODE_TOOL_NAME,   // Plan mode is main-thread only
  ASK_USER_QUESTION_TOOL_NAME, // Sub-agents don't talk to users directly
  TASK_STOP_TOOL_NAME,         // Requires main thread task state
])
```

No agent definition can override this — these tools are removed before any agent-specific filtering.

### 2.3 Context Filters: Async, Teammate, Coordinator

Different execution contexts get different tool pools:

```typescript
// reference/src/constants/tools.ts:55-71
export const ASYNC_AGENT_ALLOWED_TOOLS = new Set([
  FILE_READ_TOOL_NAME, WEB_SEARCH_TOOL_NAME, GREP_TOOL_NAME,
  GLOB_TOOL_NAME, WEB_FETCH_TOOL_NAME, FILE_EDIT_TOOL_NAME,
  FILE_WRITE_TOOL_NAME, NOTEBOOK_EDIT_TOOL_NAME,
  ...SHELL_TOOL_NAMES, SKILL_TOOL_NAME, /* ~15 tools total */
])

// reference/src/constants/tools.ts:77-88
export const IN_PROCESS_TEAMMATE_ALLOWED_TOOLS = new Set([
  TASK_CREATE_TOOL_NAME, TASK_GET_TOOL_NAME,
  TASK_LIST_TOOL_NAME, TASK_UPDATE_TOOL_NAME,
  SEND_MESSAGE_TOOL_NAME, /* +cron tools if feature-gated */
])

// reference/src/constants/tools.ts:107-112
export const COORDINATOR_MODE_ALLOWED_TOOLS = new Set([
  AGENT_TOOL_NAME,           // Spawn sub-agents
  TASK_STOP_TOOL_NAME,       // Manage tasks
  SEND_MESSAGE_TOOL_NAME,    // Communicate
  SYNTHETIC_OUTPUT_TOOL_NAME, // Generate output
])
```

The Coordinator gets only 4 tools because its job is to dispatch — not to search, edit, or execute. This is the "4-5 tools per agent" principle in practice.

### 2.4 Resolution: `resolveAgentTools()`

After `filterToolsForAgent()`, `resolveAgentTools()` applies the agent's own `disallowedTools`, expands wildcards, and validates that requested tool names actually exist:

```typescript
// reference/src/tools/AgentTool/agentToolUtils.ts:122-173
export function resolveAgentTools(agentDefinition, availableTools, isAsync, isMainThread) {
  // 1. Apply filterToolsForAgent (global + context layers)
  // 2. Build disallowed set from agent's disallowedTools
  // 3. Filter remaining tools against disallowed set
  // 4. If wildcard: return all surviving tools
  // 5. If explicit list: validate each name, collect valid/invalid
  return { hasWildcard, validTools, invalidTools, resolvedTools }
}
```

The key insight: tool allocation is declarative (what you write in the agent definition) but enforcement is layered (multiple runtime filters stack on top).

---

## Part 3: Built-In Agent Scoping Strategies

Claude Code's built-in agents demonstrate a spectrum of tool allocation strategies. Each represents a different design trade-off.

### 3.1 Minimal Allowlist: STATUSLINE_SETUP_AGENT

```typescript
// reference/src/tools/AgentTool/built-in/statuslineSetup.ts:134-144
tools: ['Read', 'Edit'],  // 2 tools only
model: 'sonnet',
color: 'orange',
```

**Strategy**: Explicit allowlist with the absolute minimum. This agent reads a config file and edits it — nothing else is relevant. Giving it Bash or WebSearch would only create opportunities for misuse.

### 3.2 Blocklist for Read-Only: EXPLORE_AGENT and PLAN_AGENT

```typescript
// reference/src/tools/AgentTool/built-in/exploreAgent.ts:64-73
disallowedTools: [AGENT_TOOL_NAME, EXIT_PLAN_MODE_TOOL_NAME,
  FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME, NOTEBOOK_EDIT_TOOL_NAME],
omitClaudeMd: true,  // Also strips CLAUDE.md context to save tokens
```

```typescript
// reference/src/tools/AgentTool/built-in/planAgent.ts:84
tools: EXPLORE_AGENT.tools,  // Reuses Explore's tool configuration
```

**Strategy**: Block destructive tools, inherit everything else. Both agents need flexible read access (Glob, Grep, Read, WebFetch, WebSearch, Bash for read-only commands) but must never modify files. The Plan agent reuses Explore's configuration directly — shared constraints stay in sync.

### 3.3 Conditional Tools: CLAUDE_CODE_GUIDE_AGENT

```typescript
// reference/src/tools/AgentTool/built-in/claudeCodeGuideAgent.ts:106-117
tools: hasEmbeddedSearchTools()
  ? [BASH_TOOL_NAME, FILE_READ_TOOL_NAME, WEB_FETCH_TOOL_NAME, WEB_SEARCH_TOOL_NAME]
  : [GLOB_TOOL_NAME, GREP_TOOL_NAME, FILE_READ_TOOL_NAME,
     WEB_FETCH_TOOL_NAME, WEB_SEARCH_TOOL_NAME],
permissionMode: 'dontAsk',
model: 'haiku',
```

**Strategy**: Dynamic allowlist based on runtime capabilities. When embedded search tools exist, the agent uses Bash (which wraps them); otherwise it falls back to Glob + Grep. The `permissionMode: 'dontAsk'` is safe because the tools are all read-only.

### 3.4 Full Access Wildcard: GENERAL_PURPOSE_AGENT

```typescript
// reference/src/tools/AgentTool/built-in/generalPurposeAgent.ts:25-34
tools: ['*'],
// model intentionally omitted — uses getDefaultSubagentModel()
```

**Strategy**: Maximum flexibility for a general-purpose research and execution agent. Still subject to `ALL_AGENT_DISALLOWED_TOOLS` and context-based filtering — the wildcard is "all available after runtime filters", not "all tools unconditionally".

### 3.5 Background + Safety: VERIFICATION_AGENT

```typescript
// reference/src/tools/AgentTool/built-in/verificationAgent.ts:139-154
disallowedTools: [AGENT_TOOL_NAME, EXIT_PLAN_MODE_TOOL_NAME,
  FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME, NOTEBOOK_EDIT_TOOL_NAME],
background: true,
criticalSystemReminder_EXPERIMENTAL:
  'CRITICAL: This is a VERIFICATION-ONLY task. You CANNOT edit, write, or create files...',
```

**Strategy**: Same blocklist as Explore, but adds defense in depth. The `background: true` flag means it runs asynchronously, and `criticalSystemReminder_EXPERIMENTAL` reinjects the constraint at every turn — belt and suspenders for a high-stakes read-only role.

### 3.6 The Tool Scoping Spectrum

| Agent | Strategy | Tool Count | Key Design Choice |
|-------|----------|-----------|-------------------|
| STATUSLINE_SETUP | Explicit allowlist | 2 | Absolute minimum for the task |
| CLAUDE_CODE_GUIDE | Conditional allowlist | 4-5 | Dynamic based on runtime capabilities |
| EXPLORE / PLAN | Blocklist (read-only) | ~10+ | Block destructive, inherit all read tools |
| VERIFICATION | Blocklist + reminders | ~10+ | Same as Explore + defense in depth |
| GENERAL_PURPOSE | Wildcard `['*']` | All available | Maximum flexibility, filtered by runtime |
| COORDINATOR | Context allowlist | 4 | Only dispatch tools, no execution |

---

## Part 4: Tool Buckets and Categories

### 4.1 ToolSelector Buckets

Claude Code's UI for custom agent configuration categorizes tools into semantic buckets:

```typescript
// reference/src/components/agents/ToolSelector.tsx:49-74
READ_ONLY: { toolNames: new Set([Glob, Grep, FileRead, WebFetch, WebSearch, ...]) }
EDIT:      { toolNames: new Set([FileEdit, FileWrite, NotebookEdit]) }
EXECUTION: { toolNames: new Set([Bash]) }
MCP:       { toolNames: new Set() }  // Dynamic — discovered at runtime
OTHER:     { toolNames: new Set() }  // Catch-all
```

### 4.2 Using Buckets as Design Heuristics

When designing a new agent, start by asking which bucket levels it needs:

1. **READ_ONLY only** — information gathering, analysis, verification agents
2. **READ_ONLY + EDIT** — agents that modify files but don't run arbitrary commands
3. **READ_ONLY + EDIT + EXECUTION** — full development agents that run builds, tests, etc.
4. **MCP** — external service integrations; these bypass built-in filtering and deserve separate review

If your agent doesn't need EXECUTION tools, don't give them. If it doesn't need EDIT tools, exclude them. Each bucket level you omit reduces the agent's attack surface and improves tool selection accuracy.

---

## Part 5: tool_choice Configuration

While tool allocation controls what an agent *can* use, `tool_choice` controls what the model *must* use on a specific API call.

### 5.1 Auto Mode (Default): `undefined`

When `tool_choice` is omitted or `undefined`, the model decides freely whether to call a tool and which one. This is the default for all conversational and agentic loops:

```typescript
// reference/src/services/api/claude.ts:1710-1712
tools: allTools,
tool_choice: options.toolChoice,  // undefined = auto
```

Use auto mode when the model needs reasoning freedom — the main conversation loop, agent execution loops, and any scenario where the model should decide its own next action.

### 5.2 Forced Selection: `{ type: 'tool', name: '...' }`

Forced selection guarantees the model calls a specific tool. This is used for structured extraction side queries where the model serves as a classification or extraction engine:

```typescript
// reference/src/utils/permissions/permissionExplainer.ts:178-186
const response = await sideQuery({
  tools: [EXPLAIN_COMMAND_TOOL],
  tool_choice: { type: 'tool', name: 'explain_command' },
  // Model MUST call explain_command — guaranteed structured output
})
```

The "single tool + forced selection" pattern provides 100% structured output — the model has no choice but to call the tool and populate its schema.

### 5.3 Conditional Switching Pattern

Sometimes you want forced selection for weaker models but auto for stronger ones:

```typescript
// reference/src/tools/WebSearchTool/WebSearchTool.ts:281
toolChoice: useHaiku ? { type: 'tool', name: 'web_search' } : undefined,
```

Haiku (small/fast model) is less reliable at tool selection, so the code forces it to call `web_search`. The main model gets `undefined` (auto) because it can decide correctly on its own. This pattern treats `tool_choice` as a **compensation mechanism for model capability gaps**.

### 5.4 Decision Rule: When to Force vs Auto

| Scenario | tool_choice | Reasoning |
|----------|------------|-----------|
| Main conversation loop | `undefined` (auto) | Model needs reasoning freedom |
| Agent execution loop | `undefined` (auto) | Agent needs to choose between multiple tools |
| Structured extraction side query | `{ type: 'tool', name: '...' }` | Guaranteed schema-conformant output |
| Weaker model in specific role | `{ type: 'tool', name: '...' }` | Compensate for unreliable selection |
| Pipeline step that MUST act | `"any"` | Model must call *some* tool, but can choose which |

**Key insight**: `"any"` (model must call a tool but can choose which) is rarely used in Claude Code because tool allocation is already precise enough that auto mode works. It's most useful in automation pipelines where every step must execute an action and the model should never just return text.

---

## Part 6: Agent Schema Definition Patterns

### 6.1 BaseAgentDefinition Common Fields

Every agent — built-in, custom, or plugin — shares these fields:

```typescript
// reference/src/tools/AgentTool/loadAgentsDir.ts:106-133
export type BaseAgentDefinition = {
  agentType: string              // Unique identifier (e.g., 'Explore', 'Plan')
  whenToUse: string              // Description for the parent agent's tool selection
  tools?: string[]               // Allowlist (or ['*'] for all)
  disallowedTools?: string[]     // Blocklist
  model?: string                 // 'inherit', 'haiku', 'sonnet', or explicit model ID
  permissionMode?: PermissionMode // 'default' | 'plan' | 'acceptEdits' | 'dontAsk' | ...
  maxTurns?: number              // Safety limit on agentic turns
  background?: boolean           // Run asynchronously
  isolation?: 'worktree' | 'remote' // Isolated execution environment
  mcpServers?: AgentMcpServerSpec[] // Agent-specific MCP servers
  hooks?: HooksSettings          // Session-scoped hooks
  memory?: AgentMemoryScope      // 'user' | 'project' | 'local'
  omitClaudeMd?: boolean         // Strip CLAUDE.md to save tokens
  // ...
}
```

### 6.2 BuiltInAgentDefinition: Dynamic System Prompts

Built-in agents extend the base with a `getSystemPrompt()` function that receives runtime context:

```typescript
// reference/src/tools/AgentTool/loadAgentsDir.ts:136-143
export type BuiltInAgentDefinition = BaseAgentDefinition & {
  source: 'built-in'
  baseDir: 'built-in'
  callback?: () => void
  getSystemPrompt: (params: {
    toolUseContext: Pick<ToolUseContext, 'options'>
  }) => string
}
```

This enables prompts that adapt to current configuration — the Claude Code Guide agent, for example, injects the list of currently configured MCP servers and custom skills into its system prompt.

### 6.3 AgentJsonSchema with `lazySchema()`

Custom agents defined in JSON files (`.claude/agents/`) are validated against a Zod schema. The schema uses `lazySchema()` to defer construction and break circular import chains:

```typescript
// reference/src/utils/lazySchema.ts:1-8
export function lazySchema<T>(factory: () => T): () => T {
  let cached: T | undefined
  return () => (cached ??= factory())  // Construct on first call, cache thereafter
}

// reference/src/tools/AgentTool/loadAgentsDir.ts:73-98
const AgentJsonSchema = lazySchema(() =>
  z.object({
    description: z.string().min(1),        // Required: what the agent does
    tools: z.array(z.string()).optional(),  // Optional allowlist
    disallowedTools: z.array(z.string()).optional(), // Optional blocklist
    prompt: z.string().min(1),             // Required: system prompt content
    model: z.string().optional(),          // Optional model override
    permissionMode: z.enum(PERMISSION_MODES).optional(),
    maxTurns: z.number().int().positive().optional(),
    background: z.boolean().optional(),
    isolation: z.enum(['worktree']).optional(),
    // ... other optional fields
  }),
)
```

The `lazySchema` pattern matters because `loadAgentsDir.ts` is imported early in the module graph, and the schemas it references (HooksSchema, McpServerConfigSchema) have their own dependency chains. Deferring construction prevents circular initialization errors.

### 6.4 The Type Hierarchy: Built-In / Custom / Plugin

```typescript
// reference/src/tools/AgentTool/loadAgentsDir.ts:162-166
export type AgentDefinition =
  | BuiltInAgentDefinition   // Source code agents with dynamic prompts
  | CustomAgentDefinition    // User-defined .md/.json agents
  | PluginAgentDefinition    // Plugin-provided agents
```

All three types share `BaseAgentDefinition` fields, so the tool allocation and filtering pipeline works identically regardless of how the agent was defined. The difference is in system prompt construction: built-in agents get runtime context via `getSystemPrompt(params)`, while custom and plugin agents use static prompts.

---

## Quick Reference: Agent Tool Allocation Checklist

When designing or reviewing agent tool boundaries, verify:

- [ ] Every agent has an explicit tool scoping strategy — allowlist, blocklist, or wildcard with justification
- [ ] Narrow-purpose agents use allowlists (`tools: ['Read', 'Edit']`), not wildcards
- [ ] Read-only agents blocklist destructive tools (Edit, Write, Notebook) or use a read-only allowlist
- [ ] No agent attempts to override `ALL_AGENT_DISALLOWED_TOOLS` (TaskOutput, ExitPlanMode, AskUserQuestion, TaskStop)
- [ ] Async agents are tested against `ASYNC_AGENT_ALLOWED_TOOLS` — tools outside this set are silently dropped
- [ ] MCP tools are reviewed separately — they bypass `filterToolsForAgent`'s built-in checks
- [ ] `tool_choice` is `undefined` for conversational and agentic loops (model needs reasoning freedom)
- [ ] `tool_choice` is forced (`{ type: 'tool', name: '...' }`) only for structured extraction side queries
- [ ] Agent schemas use `lazySchema()` when Zod definitions have circular module dependencies
- [ ] `BuiltInAgentDefinition` uses `getSystemPrompt()` (dynamic) for runtime-adaptive prompts
- [ ] Custom agent JSON definitions include required fields: `description` and `prompt`
- [ ] Tool scoping and system prompt are coherent — the prompt does not reference tools the agent cannot access
- [ ] The `whenToUse` description accurately reflects the agent's tool capabilities so the parent agent dispatches correctly

---

## See Also

- **`skill-builder`** — End-to-end skill creation: intent capture, frontmatter design, scaffolding, and optional test-iterate. Use that skill when building a new skill from scratch; come here when you need detailed agent-level tool boundary guidance.
- **`mcp-tool-design`** — Design-level principles for tool descriptions, input/output contracts, tool splitting, and routing. Start there when designing the *content* of tools themselves; come here when deciding which tools each agent should access and how `tool_choice` should be configured.
- **`mcp-error-response`** — Error response design for MCP tools: classification, the `isError` flag, retryable vs non-retryable, and subagent error propagation. Use that skill when your agent's tools are allocated but you need to design how errors are reported and handled across agent boundaries.
- **`mcp-tool-enhancement`** — Platform-level optimization: `searchHint`, `alwaysLoad`, annotations, and `.mcp.json` configuration. Use that skill when your agent's tool allocation is settled and you need to make MCP tools discoverable and competitive within the tool pool.
