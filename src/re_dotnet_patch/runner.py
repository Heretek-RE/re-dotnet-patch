"""Subprocess wrapper around the .NET ``patcher-cli``.

The Mono.Cecil round-trip patcher is built once via ``dotnet publish``
(see ``install.sh``) and stored at
``<server>/bin/patcher-cli``. The C# project is at
``servers/re-dotnet-patch/dotnet/Patcher.Cli/``.

This module locates the binary, runs one subcommand, and returns
the parsed JSON the underlying tool produces. Mirrors the
:mod:`re_dotnet.runner` 4-step binary-locator + ``run_subcommand``
pattern verbatim — the only difference is the binary name and
the env-var name.

Keeping the subprocess boundary here means the MCP server itself
stays pure Python — no pythonnet, no in-process CLR, no fragile
.NET-host APIs. The .NET dependency is contained to one published
executable that the user can replace without touching Python.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


# ── Locate the binary ─────────────────────────────────────────────────


_CLI_NAME = "patcher-cli"


def _binary_path(name: str, env_var: str) -> Path | None:
    """Return the path to a binary, or None if not found.

    Search order (mirrors re-dotnet/runner.py):
      1. env_var override (escape hatch for tests / CI)
      2. ``<server_root>/bin/<name>`` (install.sh's default)
      3. ``<name>`` on PATH
    """
    override = os.environ.get(env_var)
    if override and Path(override).is_file():
        return Path(override)

    server_root = Path(__file__).resolve().parent.parent.parent  # servers/re-dotnet-patch
    default = server_root / "bin" / name
    if default.is_file() and os.access(default, os.X_OK):
        return default

    on_path = shutil.which(name)
    if on_path:
        return Path(on_path)

    return None


def _cli_binary() -> Path | None:
    return _binary_path(_CLI_NAME, "RE_DOTNET_PATCH_CLI_PATH")


# ── Run a patcher subcommand ──────────────────────────────────────────


def run_subcommand(
    subcommand: str,
    *args: str,
    timeout_s: int = 120,
) -> dict[str, Any]:
    """Invoke the .NET patcher CLI with ``subcommand`` + extra args, parse JSON.

    Returns a dict. On error, returns ``{"error": str, "exit_code": int}``.
    """
    binary = _cli_binary()
    if binary is None:
        return {
            "error": (
                "patcher-cli not found. Run install.sh (or "
                "`dotnet publish` inside "
                "src/re_dotnet_patch/dotnet/Patcher.Cli) to build "
                "the .NET helper."
            ),
            "exit_code": -1,
        }

    cmd = [str(binary), subcommand, *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "error": f"patcher-cli {subcommand} timed out after {timeout_s}s",
            "exit_code": -1,
        }
    except FileNotFoundError as exc:
        return {"error": f"failed to exec {binary}: {exc}", "exit_code": -1}

    # The CLI always prints one JSON document on stdout (or stderr on error).
    output = (proc.stdout or "").strip()
    if not output:
        err = (proc.stderr or "").strip()
        return {
            "error": err or f"patcher-cli exited {proc.returncode} with no output",
            "exit_code": proc.returncode,
        }

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        return {
            "error": f"non-JSON output from patcher-cli: {exc}; raw={output[:500]}",
            "exit_code": proc.returncode,
        }

    if proc.returncode != 0 or (isinstance(parsed, dict) and "error" in parsed):
        return {
            "error": parsed.get("error", "unknown error")
            if isinstance(parsed, dict)
            else "non-dict error payload",
            "exit_code": proc.returncode,
        }
    return parsed if isinstance(parsed, dict) else {"result": parsed}
