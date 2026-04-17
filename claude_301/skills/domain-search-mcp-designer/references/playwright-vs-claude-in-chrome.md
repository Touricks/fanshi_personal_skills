# Playwright MCP vs. Claude-in-Chrome MCP

Read this before picking the browser backend for a new domain server. The two backends have real, persistent tradeoffs — the wrong choice produces either "server never works in production" (Playwright, if storage-state is untenable) or "server has too much access to the user's accounts" (Claude-in-Chrome, if isolation matters).

## The core question

**Who owns the browser session the server uses?**

- **Playwright** — the server owns it. It launches a fresh browser each run, loads a cookie file you produced offline, and has access to exactly what that cookie file grants.
- **Claude-in-Chrome** — the user owns it. The server drives the user's already-open Chrome. Every tab, every site the user is logged into, is reachable.

## Side-by-side

| Dimension              | Playwright MCP                              | Claude-in-Chrome MCP                       |
|------------------------|---------------------------------------------|--------------------------------------------|
| Auth surface           | One `storage_state.json` per target domain  | Whatever Chrome already has (all sites)    |
| Cookie source          | Offline `playwright codegen` capture        | User's live Chrome profile                 |
| Isolation              | Per-domain, per-run                         | None — full Chrome profile                 |
| Region restrictions    | Same as the machine running Playwright      | Same as the user's Chrome                  |
| Setup cost             | Medium — one-time codegen per domain        | Low — Chrome already logged in             |
| Refresh cost           | Manual re-codegen when cookies expire       | Automatic — user's session stays logged in |
| Bot-detection posture  | Often flagged (headless fingerprint)        | Indistinguishable from real user           |
| Reproducibility        | High — stored state is portable             | Low — depends on user's machine            |
| Production readiness   | High                                        | Low — meant for the developer's workstation|

## Pick Playwright when…

- The site has a stable login flow and reasonable cookie lifetimes (weeks/months).
- You need the server to run unattended on a build machine or server.
- The same scaffold may be shared across teammates — they each generate their own `storage_state.json`.
- You care about isolation: the server should only be able to reach the target domain.

## Pick Claude-in-Chrome when…

- The target domain has aggressive bot detection (Xiaohongshu, Dianping, LinkedIn, some Chinese social platforms) that flags Playwright's fingerprint within minutes.
- You cannot install Playwright on the machine (corp proxy, restricted VM).
- The server runs on your workstation for interactive research — never production.
- Cookies expire frequently and manually refreshing `storage_state.json` would be painful.

## Fallback logic

The scaffold's default is Playwright. If, at runtime, the Playwright backend detects that its storage state is missing, expired, or being challenged by the target, it should:

1. Log a structured warning.
2. Emit an MCP `content` block to the calling agent suggesting the user re-run with `browser_backend=claude_in_chrome` for this session.
3. Refuse to proceed silently with unauthenticated requests (that reliably produces either rate-limits or degraded results, both of which corrupt downstream reports).

## Auth surface

Cookies expire. Pick a refresh plan before you ship.

Options, in order of robustness:

1. **Manual refresh on a cadence.** Cron a reminder to re-run `playwright codegen --save-storage=…` every N days. Simple, reliable, doesn't scale past ~3 domains.
2. **Semi-automated refresh.** A separate tool the user runs interactively to re-authenticate; it writes the fresh `storage_state.json` and restarts the server. Good balance for small teams.
3. **Browser-extension capture.** A tiny Chrome extension that, when the user is logged into the target, exports cookies to the same `storage_state.json` path. Most seamless for long-lived servers; highest upfront build cost.

Whatever you pick, **never check `storage_state.json` into source control**. Put it at a per-user path (`~/.config/<server_pkg>/storage_state.json`) and add the equivalent to `.gitignore`.

## Security boundary

This is the one the Claude-in-Chrome route weakens. When the server can drive your real Chrome, it can, in principle, request any page that Chrome has a session for — not just the target domain. Three mitigations:

- **Never run Claude-in-Chrome against an agent you haven't audited.** The upstream agent's tool-use policy is now your de-facto auth boundary.
- **Run the server as your own user, not a shared service account.** Limits blast radius if the agent misbehaves.
- **Log every URL the server navigates to.** Rotate the log; inspect after high-stakes sessions.

For any production deployment — where the server accepts requests from untrusted upstream agents — use Playwright with a narrowly scoped `storage_state.json`.
