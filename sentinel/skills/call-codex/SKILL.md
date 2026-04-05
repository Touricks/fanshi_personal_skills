---
name: call-codex
description: Ask OpenAI Codex CLI for a second opinion, critique, or analysis from within a Claude Code session. Use when the user says "ask codex", "call codex", "get codex's opinion", "second opinion from codex", "codex review", or wants to consult Codex on code, architecture, or any technical question. Requires codex-cli installed (`codex` binary available in PATH).
---

# Call Codex (Hardened)

Invoke OpenAI Codex CLI non-interactively to get a second opinion or critique, then present the result.

## Command Pattern

Each invocation MUST use `mktemp` for atomic unique path creation and restrict permissions:

```bash
umask 077
CODEX_OUT=$(mktemp /tmp/codex_output_XXXXXXXX)
```

### Standard invocation (no web search)

```bash
cat <<'PROMPT' | codex exec --full-auto --skip-git-repo-check --ephemeral -o "$CODEX_OUT" -
<your prompt here>
Do NOT modify any files. Do NOT run any shell commands. Only output your analysis as text.
PROMPT
```

### Web search invocation (for current/real-time information)

When the prompt explicitly requires current or real-time information (news, latest versions, recent events), place `--search` **before** the `exec` subcommand:

```bash
cat <<'PROMPT' | codex --search exec --full-auto --skip-git-repo-check --ephemeral -o "$CODEX_OUT" -
<your prompt here>
Do NOT modify any files. Do NOT run any shell commands. Only output your analysis as text.
PROMPT
```

**Important:** `--search` is a top-level `codex` flag, NOT an `exec` flag. It must come before `exec`.

### Structured output invocation (for JSON responses)

When the caller wants structured JSON output, write a JSON Schema to a temp file and pass it via `--output-schema`:

```bash
SCHEMA_FILE=$(mktemp /tmp/codex_schema_XXXXXXXX)
cat > "$SCHEMA_FILE" <<'SCHEMA'
{ "type": "object", "properties": { ... }, "required": [ ... ] }
SCHEMA

cat <<'PROMPT' | codex exec --full-auto --skip-git-repo-check --ephemeral --output-schema "$SCHEMA_FILE" -o "$CODEX_OUT" -
<your prompt here>
Do NOT modify any files. Do NOT run any shell commands.
PROMPT

rm -f "$SCHEMA_FILE"
```

Then read `$CODEX_OUT` for the clean response.

## Workflow

1. **Construct the prompt.** Combine the user's request with relevant context (file contents, code snippets, error messages). Always append: `Do NOT modify any files. Do NOT run any shell commands. Only output your analysis as text.`

2. **Determine invocation mode:**
   - If the prompt requires current/real-time information → use web search invocation
   - If the caller wants structured JSON → use structured output invocation
   - Otherwise → use standard invocation

3. **Generate a secure unique output path.** Use `mktemp` with `umask 077`:
   ```bash
   umask 077
   CODEX_OUT=$(mktemp /tmp/codex_output_XXXXXXXX)
   ```

4. **Run the command with timeout.** Wrap the invocation with a timeout supervisor (180s default). On macOS, use a background watchdog pattern since GNU `timeout` is not available:
   ```bash
   TIMEOUT_SECS=180
   (
     cat <<'PROMPT' | codex exec --full-auto --skip-git-repo-check --ephemeral -o "$CODEX_OUT" -
   <prompt>
   PROMPT
   ) &
   CODEX_PID=$!
   ( sleep "$TIMEOUT_SECS" && kill -TERM "$CODEX_PID" 2>/dev/null ) &
   WATCHDOG_PID=$!
   wait "$CODEX_PID" 2>/dev/null
   CODEX_RC=$?
   kill "$WATCHDOG_PID" 2>/dev/null
   wait "$WATCHDOG_PID" 2>/dev/null 2>&1
   ```
   **IMPORTANT:** Do NOT use `run_in_background`. The output file must be fully written before reading.

5. **Classify the result.** Use the error classification table below.

6. **Retry if eligible.** If the failure is transient (empty/missing output only), retry **once** with a fresh `mktemp` path. Preserve the first attempt's exit code and stderr for diagnostics. Do NOT retry non-zero exits from codex itself — those indicate deterministic failures.

7. **Read the output.** Read the file at `$CODEX_OUT` for Codex's response. The `-o` file contains only the agent's final message (stdout includes session metadata).

8. **Clean up.** Remove the temp output file after reading:
   ```bash
   rm -f "$CODEX_OUT"
   ```

9. **Present the result.** Summarize or relay Codex's response to the user. If the user asked for a comparison, contrast Codex's view with your own.

## Error Classification

After running codex, classify the outcome:

| Condition | Category | Retryable? | Action |
|-----------|----------|------------|--------|
| `command -v codex` fails | `codex-not-installed` | No | Tell user: install with `brew install codex` or see OpenAI docs |
| Exit code 137/143 or watchdog killed | `timed-out` | No | Report timeout, suggest increasing TIMEOUT_SECS or simplifying prompt |
| `$CODEX_OUT` does not exist | `empty-output` | Yes (once) | Retry with fresh mktemp path |
| `$CODEX_OUT` exists but is empty (0 bytes) | `empty-output` | Yes (once) | Retry with fresh mktemp path |
| Non-zero exit + stderr contains "auth" or "login" or "unauthorized" | `auth-failed` (best-effort) | No | Tell user to run `codex login` or check credentials |
| Any other non-zero exit | `exec-error` | No | Report exit code and stderr to user for diagnosis |
| Exit 0 + non-empty output | `success` | N/A | Present result |

**Retry rules:**
- Only retry `empty-output` conditions — these are plausibly transient
- Wait 3 seconds before retry
- Use a fresh `mktemp` path for the retry attempt
- Preserve first attempt's exit code and stderr — report both if retry also fails
- Never retry prompts that the user marked as having side effects

## Key Flags

| Flag | Purpose |
|------|---------|
| `exec` | Non-interactive subcommand (required for scripted use) |
| `--full-auto` | Skips confirmation prompts (alias for `-a on-request --sandbox workspace-write`) |
| `--skip-git-repo-check` | Run outside or independent of current git repo |
| `--ephemeral` | No persistent session state on disk (stateless by design) |
| `-o "$CODEX_OUT"` | Write final message to unique file for clean reading |
| `-` (trailing) | Read prompt from stdin (avoids shell quoting issues) |
| `--search` | **Top-level flag** (before `exec`): enable native web search tool |
| `--output-schema <FILE>` | Path to JSON Schema file for structured output validation |

## Optional Flags

- `-m <model>` to override the default model (default: `gpt-5.4`)
- `-C /path` to set a different working directory for Codex

## Example

User asks: "Ask codex to review my sort function in utils.py"

1. Read `utils.py` to get the sort function code
2. Run:
```bash
umask 077
CODEX_OUT=$(mktemp /tmp/codex_output_XXXXXXXX)
cat <<'PROMPT' | codex exec --full-auto --skip-git-repo-check --ephemeral -o "$CODEX_OUT" -
Review the following Python sort function for correctness, efficiency, and style:

<contents of the sort function>

Do NOT modify any files. Do NOT run any shell commands. Only output your critique as text.
PROMPT
```
3. Read the file at `$CODEX_OUT` (the unique path from mktemp)
4. Present Codex's feedback to the user
5. Clean up: `rm -f "$CODEX_OUT"`

## Example: Web search for current information

User asks: "Ask codex what the latest React version is and what changed"

```bash
umask 077
CODEX_OUT=$(mktemp /tmp/codex_output_XXXXXXXX)
cat <<'PROMPT' | codex --search exec --full-auto --skip-git-repo-check --ephemeral -o "$CODEX_OUT" -
What is the latest stable version of React? What are the key changes in this release?

Do NOT modify any files. Do NOT run any shell commands. Only output your analysis as text.
PROMPT
```

## Important Notes

- **NEVER use a fixed output path** like `/tmp/codex_output.md`. Always use `mktemp` for atomic unique file creation.
- **NEVER use `run_in_background`** for the codex command. The output file must be fully written before you read it. Running in background causes a race condition.
- **Use `umask 077`** before `mktemp` to restrict temp file permissions (owner read/write only). This prevents other users from reading prompt content or responses.
- Always include the safety instruction ("Do NOT modify any files...") since `--full-auto` grants write access to the sandbox.
- Use single-quoted heredoc delimiter `'PROMPT'` to prevent `$variable` expansion and `` `backtick` `` execution in the prompt text.
- Use `--ephemeral` to avoid accumulating session state on disk for one-shot analysis calls.
- If `codex` is not found, inform the user to install it (`brew install codex` or see OpenAI docs).
- If the output seems unrelated to your prompt, suspect stale output — delete the file, generate a fresh `mktemp` path, and re-run.
- The `--search` flag goes **before** `exec`, not after. `codex --search exec ...` is correct; `codex exec --search ...` is NOT.
- When retrying, always report both attempts' diagnostics so failures are not masked.
