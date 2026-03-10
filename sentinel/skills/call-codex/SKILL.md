---
name: call-codex
description: Ask OpenAI Codex CLI for a second opinion, critique, or analysis from within a Claude Code session. Use when the user says "ask codex", "call codex", "get codex's opinion", "second opinion from codex", "codex review", or wants to consult Codex on code, architecture, or any technical question. Requires codex-cli installed (`codex` binary available in PATH).
---

# Call Codex

Invoke OpenAI Codex CLI non-interactively to get a second opinion or critique, then present the result.

## Command Pattern

```bash
cat <<'PROMPT' | codex exec --full-auto --skip-git-repo-check -o /tmp/codex_output.md -
<your prompt here>
Do NOT modify any files. Do NOT run any shell commands. Only output your analysis as text.
PROMPT
```

Then read `/tmp/codex_output.md` for the clean response.

## Workflow

1. **Construct the prompt.** Combine the user's request with relevant context (file contents, code snippets, error messages). Always append: `Do NOT modify any files. Do NOT run any shell commands. Only output your analysis as text.`
2. **Run the command.** Use `cat <<'PROMPT' | codex exec --full-auto --skip-git-repo-check -o /tmp/codex_output.md -` with the constructed prompt. Use single-quoted heredoc delimiter (`'PROMPT'`) to prevent shell expansion.
3. **Read the output.** Read `/tmp/codex_output.md` for Codex's response. The `-o` file contains only the agent's final message (stdout includes session metadata).
4. **Present the result.** Summarize or relay Codex's response to the user. If the user asked for a comparison, contrast Codex's view with your own.

## Key Flags

| Flag | Purpose |
|------|---------|
| `exec` | Non-interactive subcommand (required for scripted use) |
| `--full-auto` | Skips confirmation prompts (alias for `-a on-request --sandbox workspace-write`) |
| `--skip-git-repo-check` | Run outside or independent of current git repo |
| `-o /tmp/codex_output.md` | Write final message to file for clean reading |
| `-` (trailing) | Read prompt from stdin (avoids shell quoting issues) |

## Optional Flags

- `-m <model>` to override the default model (default: `gpt-5.4`)
- `-C /path` to set a different working directory for Codex

## Example

User asks: "Ask codex to review my sort function in utils.py"

1. Read `utils.py` to get the sort function code
2. Run:
```bash
cat <<'PROMPT' | codex exec --full-auto --skip-git-repo-check -o /tmp/codex_output.md -
Review the following Python sort function for correctness, efficiency, and style:

```python
<contents of the sort function>
```

Do NOT modify any files. Do NOT run any shell commands. Only output your critique as text.
PROMPT
```
3. Read `/tmp/codex_output.md`
4. Present Codex's feedback to the user

## Important Notes

- Always include the safety instruction ("Do NOT modify any files...") since `--full-auto` grants write access to the sandbox.
- Use single-quoted heredoc delimiter `'PROMPT'` to prevent `$variable` expansion and `` `backtick` `` execution in the prompt text.
- If `codex` is not found, inform the user to install it (`brew install codex` or see OpenAI docs).
- Token usage is printed to stdout at the end of the session.
