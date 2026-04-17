"""Post-scaffold sanity check.

Usage:
    python validate_scaffold.py <output-dir>

Checks:
  - no placeholder leakage ("$var" or "<<IF" remnants)
  - .search-scratchpad/ exists
  - src/<pkg>/{schemas,server,translator,scratchpad,writeback}.py exist
  - Pydantic SearchResult round-trips a fixture (requires pydantic installed)

Exit code 0 on success, 1 on any failure.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

_LEAK_RE = re.compile(r"<<IF|<<ENDIF|\$\{[a-z_]+\}")
# "$word" leakage check: match "$" followed by a lowercase identifier that
# is NOT inside a string we accept (escape sequences in sample shell code).
_DOLLAR_VAR_RE = re.compile(r"\$[a-z_][a-z_0-9]*")

# Files where $-prefixed tokens are legitimate (shell examples, env vars).
_DOLLAR_ALLOWLIST = {"README.md", "mcp_config.json"}


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")


def _check_leaks(out: Path) -> list[str]:
    failures: list[str] = []
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".gitkeep"}:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if _LEAK_RE.search(text):
            failures.append(f"{path}: conditional-block or ${{}} placeholder leaked")
        if path.name not in _DOLLAR_ALLOWLIST and _DOLLAR_VAR_RE.search(text):
            # Allow $ in code comments referencing shell commands
            bad_matches = [
                m.group(0) for m in _DOLLAR_VAR_RE.finditer(text)
                # Heuristic: a bare $word on a Python line is a leak.
                # Ignore if line also contains "shell" or is inside docstring.
            ]
            # Lightweight: flag if any $identifier is found, since the
            # templates only use $-placeholders for substitution.
            if bad_matches:
                failures.append(
                    f"{path}: possible $-placeholder leak: {bad_matches[:3]}"
                )
    return failures


def _read_pkg(out: Path) -> str | None:
    pyproj = out / "pyproject.toml"
    if not pyproj.exists():
        return None
    try:
        data = tomllib.loads(pyproj.read_text())
    except tomllib.TOMLDecodeError:
        return None
    return data.get("project", {}).get("name")


def _check_layout(out: Path, pkg: str) -> list[str]:
    failures: list[str] = []
    expected = [
        f"src/{pkg}/__init__.py",
        f"src/{pkg}/schemas.py",
        f"src/{pkg}/server.py",
        f"src/{pkg}/translator.py",
        f"src/{pkg}/scratchpad.py",
        f"src/{pkg}/writeback.py",
        "pyproject.toml",
        "mcp_config.json",
        "README.md",
        ".search-scratchpad/README.md",
    ]
    for rel in expected:
        if not (out / rel).exists():
            failures.append(f"missing expected file: {rel}")
    return failures


def _check_schema_roundtrip(out: Path, pkg: str) -> list[str]:
    """Try a Pydantic import + round-trip. Skip silently if pydantic isn't
    available (validator shouldn't require the scaffold's deps)."""
    try:
        import importlib
        import importlib.util

        schemas_path = out / "src" / pkg / "schemas.py"
        spec = importlib.util.spec_from_file_location(
            f"{pkg}_schemas", schemas_path
        )
        if spec is None or spec.loader is None:
            return [f"could not load spec for {schemas_path}"]
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sr = mod.SearchResult(
            title="t",
            url="https://example.com/x",
            snippet="s",
            source_language="en",
        )
        json_str = sr.model_dump_json()
        mod.SearchResult.model_validate_json(json_str)
        return []
    except ImportError:
        return []  # pydantic not installed — skip rather than fail
    except Exception as e:
        return [f"Pydantic round-trip failed: {e}"]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_scaffold.py <output-dir>", file=sys.stderr)
        return 1
    out = Path(argv[1])
    if not out.is_dir():
        print(f"not a directory: {out}", file=sys.stderr)
        return 1

    pkg = _read_pkg(out)
    if not pkg:
        _fail("could not read [project].name from pyproject.toml")
        return 1

    all_failures: list[str] = []
    all_failures += _check_layout(out, pkg)
    all_failures += _check_leaks(out)
    all_failures += _check_schema_roundtrip(out, pkg)

    print("| Check                       | Result |")
    print("|-----------------------------|--------|")
    print(
        f"| layout ({pkg})".ljust(30)
        + "|  "
        + ("PASS" if not any("missing expected" in f for f in all_failures) else "FAIL")
        + "  |"
    )
    print(
        "| placeholder leakage         ".ljust(30)
        + "|  "
        + ("PASS" if not any("leaked" in f or "placeholder leak" in f for f in all_failures) else "FAIL")
        + "  |"
    )
    print(
        "| pydantic round-trip         ".ljust(30)
        + "|  "
        + ("PASS" if not any("round-trip" in f for f in all_failures) else "FAIL")
        + "  |"
    )
    if all_failures:
        print()
        print("Failures:")
        for f in all_failures:
            print(f"  - {f}")
        return 1
    print()
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
