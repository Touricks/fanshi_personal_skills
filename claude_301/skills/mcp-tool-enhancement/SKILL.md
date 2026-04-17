---
name: mcp-tool-enhancement
description: Guide for platform-level optimization of MCP server tools within Claude Code's tool pool. Covers discoverability (searchHint, alwaysLoad), permission classification (annotations), MCP Resources as content catalogs, and .mcp.json configuration. Use when tools aren't being selected by the model, when designing MCP Resources, or when configuring MCP server metadata. Also use when the user mentions "MCP tool not being used", "agent ignores my MCP tool", "MCP resource design", "MCP discoverability", "searchHint", "alwaysLoad", "annotations", or ".mcp.json configuration". For tool description design principles and input/output contracts, see mcp-tool-design instead.
---

# MCP Tool Enhancement Guide

Make your MCP server's tools discoverable, competitive, and efficient within Claude Code's tool ecosystem. This skill covers **platform-level optimization** — how to make your tools discoverable (`searchHint`, `alwaysLoad`), how to classify them (annotations), how to expose content catalogs (MCP Resources), and how to configure MCP servers (`.mcp.json`). For **design-level principles** of writing tool descriptions, structuring input schemas, splitting tools, and avoiding misrouting, see `mcp-tool-design`.

## Why This Matters

Claude Code has powerful built-in tools (Grep, Read, Write, Edit, Bash, Glob) that the model knows intimately. When you add MCP tools, they face three structural disadvantages:

1. **Deferred by default** — MCP tools are not included in the initial prompt. The model must discover them via ToolSearch.
2. **Built-ins win name conflicts** — `assembleToolPool()` places built-in tools first; `uniqBy` preserves insertion order, so built-ins win on duplicate names.
3. **No prior familiarity** — The model has trained extensively on built-in tool patterns but has never seen your custom tools before.

This skill teaches you how to overcome these disadvantages through strategic tool descriptions, metadata, and MCP Resources.

---

## Part 1: Enhancing Tool Descriptions

The model chooses tools based on their descriptions. A vague description means your tool loses to a familiar built-in every time.

### 1.1 Write Descriptions That Win

> For general tool description design principles (input formats, example queries, edge cases, boundary patterns, keyword sensitivity), see the `mcp-tool-design` skill. This section focuses on making your descriptions competitive with Claude Code's built-in tools.

Your `tool.description` is the single most important field for tool selection. Claude Code truncates descriptions at `MAX_MCP_DESCRIPTION_LENGTH` and appends `'... [truncated]'`, so front-load the most important information.

**Principles:**
- Lead with what makes your tool **better** than the built-in alternative
- Name the built-in it replaces and explain why yours is superior
- Include concrete output format details so the model knows what to expect
- Keep it under the truncation limit — put critical differentiators in the first 200 characters

**Bad description:**
```
"Searches code in the repository"
```
The model will always pick Grep over this — it's vague and Grep is familiar.

**Good description:**
```
"Semantic code search that finds functionally similar code even when
variable names and syntax differ. Unlike Grep (text-only matching),
this tool understands code intent — use it when searching for patterns,
refactoring targets, or similar implementations across languages.
Returns: file path, line range, similarity score, and code snippet."
```

**Good description (database tool):**
```
"Execute read-only SQL queries against the project database with
automatic schema validation and result formatting. Safer than running
SQL via Bash — enforces read-only mode, prevents injection, and formats
results as markdown tables. Use instead of Bash for any database query."
```

### 1.2 Set `_meta['anthropic/searchHint']`

Since MCP tools are deferred (not in the initial prompt), the model discovers them through ToolSearch. The `searchHint` field provides keywords that ToolSearch indexes — without it, your tool may never be found.

```typescript
// In your MCP server's tool definition
{
  name: "semantic_search",
  description: "Semantic code search that finds...",
  inputSchema: { /* ... */ },
  _meta: {
    "anthropic/searchHint": "search code find similar pattern refactor semantic meaning intent"
  }
}
```

**How to write effective searchHints:**
- Include synonyms and related terms the user might think of
- Cover both the action ("search", "find", "query") and the domain ("code", "database", "issues")
- Include terms for the problem it solves ("refactor", "duplicate", "similar")
- Keep it a flat list of keywords separated by spaces — no sentences needed
- Whitespace is collapsed and trimmed automatically

### 1.3 Set `_meta['anthropic/alwaysLoad']` for Critical Tools

If your tool is essential to the workflow and should always be available (not discovered via ToolSearch), set `alwaysLoad: true`. This makes the tool appear in the initial prompt with its full schema, just like built-in tools.

```typescript
{
  name: "deploy_preview",
  description: "Deploy a preview environment for the current branch...",
  inputSchema: { /* ... */ },
  _meta: {
    "anthropic/alwaysLoad": true
  }
}
```

**When to use `alwaysLoad`:**
- The tool is the primary reason the MCP server exists
- Users expect the tool to be immediately available without searching
- The tool handles a critical workflow step (deploy, approve, publish)

**When NOT to use it:**
- Utility or secondary tools — let ToolSearch handle discovery
- Tools with large schemas — they consume prompt tokens on every request
- Rarely-used tools — the prompt cache cost isn't worth it

### 1.4 Use Annotations for Permission Classification

Tool annotations affect how Claude Code classifies permissions and concurrency safety:

```typescript
{
  name: "query_database",
  // ...
  annotations: {
    readOnlyHint: true,    // Safe for concurrent execution, lighter permission prompt
    destructiveHint: false, // Won't destroy data
    openWorldHint: false    // Operates within project scope only
  }
}
```

| Annotation | Effect in Claude Code |
|---|---|
| `readOnlyHint: true` | Tool marked as concurrency-safe; can run in parallel with other read-only tools |
| `destructiveHint: true` | Triggers stronger permission warnings to the user |
| `openWorldHint: true` | Indicates the tool accesses external systems beyond the local project |

---

## Part 2: Designing MCP Resources as Content Catalogs

MCP Resources expose browseable content directories to the agent, eliminating expensive exploratory tool calls. Instead of the agent calling `list_projects`, then `get_project`, then `list_issues` one by one, it reads a resource catalog and jumps directly to the data it needs.

### 2.1 When to Use Resources vs Tools

| Use Resources for | Use Tools for |
|---|---|
| Directory listings, indexes, catalogs | Create, update, delete operations |
| Schema information (table structures, API shapes) | Data queries with parameters |
| Static or slowly-changing metadata | Real-time data retrieval |
| Navigation aids ("what's available?") | Execution ("do this thing") |

**Rule of thumb:** If the agent would call a tool just to learn *what's available* before calling another tool to *act on it*, the first call should be a Resource instead.

### 2.2 Resource Design Patterns

**Pattern: Project Index**
```typescript
// Expose a browseable list of all projects
server.resource("projects://index", {
  name: "Project Index",
  description: "List of all active projects with IDs, names, and status. Read this before querying project-specific data.",
  mimeType: "application/json"
}, async () => {
  const projects = await api.listProjects();
  return JSON.stringify(projects.map(p => ({
    id: p.id,
    name: p.name,
    status: p.status,
    issueCount: p.issues.length
  })));
});
```

**Pattern: Schema Catalog**
```typescript
// Expose database schema so the agent can write correct queries
server.resource("db://schema", {
  name: "Database Schema",
  description: "All table names, column names, types, and relationships. Read this before constructing any SQL query.",
  mimeType: "text/plain"
}, async () => {
  return formatSchemaAsText(await db.getSchema());
});
```

**Pattern: Hierarchical Navigation**
```typescript
// Expose a doc tree for navigating to the right document
server.resource("docs://tree", {
  name: "Documentation Tree",
  description: "Hierarchical structure of all documentation pages. Use to navigate to specific topics without searching.",
  mimeType: "application/json"
}, async () => {
  return JSON.stringify(buildDocTree());
});
```

### 2.3 Resource Descriptions That Guide the Agent

Resource descriptions tell the agent *when* to read the resource. Make them prescriptive:

**Bad:** `"Project data"`
**Good:** `"List of all active projects with IDs and names. Read this BEFORE using any project-specific tool to get the correct project ID."`

The description should answer: "When should the agent read this instead of calling a tool?"

### 2.4 Support `listChanged` Notifications

If your resource data changes (new projects added, schema migrated), implement the `resources/list_changed` notification so Claude Code refreshes its cache automatically:

```typescript
// Declare support in server capabilities
const server = new McpServer({
  capabilities: {
    resources: { listChanged: true }
  }
});

// Notify when data changes
async function onProjectCreated() {
  await server.notification({
    method: "notifications/resources/list_changed"
  });
}
```

Claude Code handles this by invalidating the resource cache and re-fetching — the agent always sees current data without manual refresh.

---

## Part 3: Configuration Best Practices

### 3.1 Project-Level `.mcp.json` for Team Tools

Shared tools go in `.mcp.json` at the project root. Use `${ENV_VAR}` for credentials:

```json
{
  "mcpServers": {
    "project-db": {
      "command": "mcp-server-postgres",
      "args": ["--read-only"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}",
        "PG_SSL": "${PG_SSL:-true}"
      }
    }
  }
}
```

The `${VAR:-default}` syntax provides fallback values when the variable is missing. Environment variable expansion covers `command`, `args`, `env`, `url`, and `headers` fields — not just `env`.

### 3.2 User-Level `~/.claude.json` for Personal Tools

Experimental or personal tools go in user config to avoid affecting teammates:

```json
// In ~/.claude.json
{
  "mcpServers": {
    "my-experiment": {
      "command": "node",
      "args": ["./my-local-mcp/index.js"]
    }
  }
}
```

### 3.3 Merge Precedence

Claude Code merges MCP configs in this order (lowest to highest priority):

```
plugin < user (~/.claude.json) < project (.mcp.json) < local
```

Later entries override earlier ones via `Object.assign`. This means a project `.mcp.json` can override a user's config for the same server name.

---

## Quick Reference: Enhancement Checklist

When building or reviewing an MCP server for Claude Code integration, verify:

- [ ] **Every tool has a detailed `description`** that explains what it does better than the built-in alternative
- [ ] **Critical differentiators are in the first 200 characters** of the description (before truncation)
- [ ] **`searchHint` metadata is set** with synonyms and related keywords for ToolSearch discovery
- [ ] **`alwaysLoad` is set to `true`** only for the 1-2 most critical tools (not all of them)
- [ ] **`annotations` are set** — especially `readOnlyHint` for query tools
- [ ] **Content catalogs are exposed as Resources**, not as `list_*` tools
- [ ] **Resource descriptions are prescriptive** — they tell the agent when to read them
- [ ] **`listChanged` notifications are implemented** if resource data changes
- [ ] **Credentials use `${ENV_VAR}` syntax** in `.mcp.json`, never hardcoded
- [ ] **Shared tools are in `.mcp.json`**, personal tools in `~/.claude.json`

---

## See Also

- **`mcp-tool-design`** — Design-level principles for tool descriptions, input/output contracts, tool splitting, misrouting avoidance, and system prompt coherence. Start there when designing tool content from scratch; come here when optimizing for Claude Code's tool pool.
- **`mcp-error-response`** — Error response design for MCP tools: classification, `isError` flag, retryable vs non-retryable, empty-vs-error, and subagent propagation. Use that skill when your tool needs structured error handling patterns before platform optimization.
