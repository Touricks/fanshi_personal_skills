"""Materialize a FastMCP domain-search-server scaffold from templates.

Usage:
    python scaffold.py --config <path-to-scaffold_config.json> --out <dir>

The agent is expected to build the config JSON from the design interview
(see SKILL.md Phase 1) and then call this script. Exit codes:

    0   success
    2   config invalid
    3   out-dir non-empty (use --force to override)
    4   template IO error
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import string
import sys
from pathlib import Path

REQUIRED_KEYS = {
    "domain_name",
    "domain_host",
    "server_pkg",
    "primary_lang",
    "browser_backend",
    "translator_mode",
}
VALID_BACKENDS = {"playwright", "claude_in_chrome"}
VALID_TRANSLATORS = {"identity", "dictionary", "llm"}

# template filename -> destination relative to out-dir
TEMPLATE_DESTS = {
    "schemas.py.tmpl": "src/{server_pkg}/schemas.py",
    "translator.py.tmpl": "src/{server_pkg}/translator.py",
    "scratchpad.py.tmpl": "src/{server_pkg}/scratchpad.py",
    "writeback.py.tmpl": "src/{server_pkg}/writeback.py",
    "server.py.tmpl": "src/{server_pkg}/server.py",
    "mcp_config.json.tmpl": "mcp_config.json",
    "pyproject.toml.tmpl": "pyproject.toml",
    "README.md.tmpl": "README.md",
}

# Matches:   # <<IF key=value>>\n ...body... # <<ENDIF>>\n
_COND_RE = re.compile(
    r"^[ \t]*#[ \t]*<<IF[ \t]+(?P<key>\w+)=(?P<value>\w+)>>[ \t]*\n"
    r"(?P<body>.*?)"
    r"^[ \t]*#[ \t]*<<ENDIF>>[ \t]*\n",
    re.DOTALL | re.MULTILINE,
)

_SERVER_PKG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _die(msg: str, code: int) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _load_config(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        _die(f"could not read/parse config at {path}: {e}", 2)
    missing = REQUIRED_KEYS - set(data)
    if missing:
        _die(f"config missing required keys: {sorted(missing)}", 2)
    if data["browser_backend"] not in VALID_BACKENDS:
        _die(
            f"browser_backend must be one of {sorted(VALID_BACKENDS)}; "
            f"got {data['browser_backend']!r}",
            2,
        )
    if data["translator_mode"] not in VALID_TRANSLATORS:
        _die(
            f"translator_mode must be one of {sorted(VALID_TRANSLATORS)}; "
            f"got {data['translator_mode']!r}",
            2,
        )
    if not _SERVER_PKG_RE.match(data["server_pkg"]):
        _die(
            f"server_pkg must match ^[a-z][a-z0-9_]*$ (snake_case); "
            f"got {data['server_pkg']!r}",
            2,
        )
    data.setdefault("python_path", "python")
    return data


def _resolve_conditionals(text: str, cfg: dict) -> str:
    """Strip out conditional blocks whose predicate does not hold; keep
    the body (minus markers) of those that do."""
    # Map the predicate keys used in templates to config keys.
    pred_map = {"browser": "browser_backend", "translator": "translator_mode"}

    def repl(m: re.Match) -> str:
        key, value, body = m.group("key"), m.group("value"), m.group("body")
        cfg_key = pred_map.get(key)
        if cfg_key is None:
            # unknown predicate — keep body as-is (fail open)
            return body
        return body if cfg.get(cfg_key) == value else ""

    return _COND_RE.sub(repl, text)


def _substitute(text: str, cfg: dict) -> str:
    # string.Template uses $var / ${var}. It leaves other $ alone when
    # safe_substitute is used, which protects f-string literals in the
    # templates' sample code blocks.
    return string.Template(text).safe_substitute(cfg)


def _materialize(templates_dir: Path, out_dir: Path, cfg: dict) -> list[Path]:
    written: list[Path] = []
    for tmpl_name, dest_rel_fmt in TEMPLATE_DESTS.items():
        src = templates_dir / tmpl_name
        try:
            raw = src.read_text()
        except OSError as e:
            _die(f"could not read template {src}: {e}", 4)
        text = _resolve_conditionals(raw, cfg)
        text = _substitute(text, cfg)
        dest_rel = dest_rel_fmt.format(server_pkg=cfg["server_pkg"])
        dest = out_dir / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(text)
        except OSError as e:
            _die(f"could not write {dest}: {e}", 4)
        written.append(dest)
    # package __init__.py
    init_path = out_dir / "src" / cfg["server_pkg"] / "__init__.py"
    init_path.write_text(f'"""FastMCP server for {cfg["domain_name"]}."""\n')
    written.append(init_path)
    # scratchpad dir
    scratch = out_dir / ".search-scratchpad"
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / ".gitkeep").touch()
    (scratch / "README.md").write_text(
        "# Search scratchpad\n\n"
        "Each top-level search creates a `<qhash>/` subdirectory here.\n"
        "`meta.json` records the original query, its translation, and the\n"
        "backend used. Per-source summaries land as `NNN-<host>.md`.\n\n"
        "The writeback tool reads these files back into a single report\n"
        "with a `## Sources` section.\n"
    )
    written.append(scratch / "README.md")
    (out_dir / "tests").mkdir(exist_ok=True)
    return written


def _print_todo(cfg: dict, out_dir: Path) -> None:
    print(f"Scaffold written to {out_dir.resolve()}")
    print()
    print("Next steps:")
    print(
        "  [ ] Credential storage strategy — see the skill's "
        "references/playwright-vs-claude-in-chrome.md#auth-surface"
    )
    print(
        "  [ ] Tune translator stub in "
        f"src/{cfg['server_pkg']}/translator.py (mode: {cfg['translator_mode']})"
    )
    print(
        f"  [ ] Implement _browser_search in src/{cfg['server_pkg']}/server.py "
        f"(backend: {cfg['browser_backend']})"
    )
    print(
        f"  [ ] Implement fetch_detail in src/{cfg['server_pkg']}/server.py"
    )
    print(
        f"  [ ] Set rate-limit policy in "
        f"src/{cfg['server_pkg']}/server.py:SEARCH_RATE_LIMIT_PER_MINUTE"
    )
    print("  [ ] Register server in your MCP client (see mcp_config.json)")
    print("  [ ] Run: uv pip install -e . && python -m " + cfg["server_pkg"])
    if cfg["browser_backend"] == "claude_in_chrome":
        print(
            "  [!] Backend = claude_in_chrome — your logged-in Chrome "
            "session is reachable by this server. Read the tradeoff doc "
            "before production use."
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument(
        "--force", action="store_true", help="Overwrite a non-empty out-dir."
    )
    args = ap.parse_args(argv)

    cfg = _load_config(args.config)

    out: Path = args.out
    if out.exists() and any(out.iterdir()):
        if not args.force:
            _die(f"output directory {out} is not empty (use --force)", 3)
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    if not templates_dir.is_dir():
        _die(f"templates directory not found at {templates_dir}", 4)

    _materialize(templates_dir, out, cfg)
    _print_todo(cfg, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
