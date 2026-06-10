"""Round-trip patcher for Mono / .NET assemblies.

v2.8.0 (WS-7): SKELETON. The MCP tool surface was final and the
return shapes were pinned by tests, but the actual round-trip
patcher backend (Mono.Cecil via a CLI shim) shipped in v2.8.1.
Every mutating operation now goes through ``runner.run_subcommand``
which calls the published ``patcher-cli`` at
``<server>/bin/patcher-cli``. Round-trip type-graph preservation
is the proof of safety (the CD-3 contract); see
``See the RE-AI output directory.``.

The ``rollback_patch`` tool remains a ``status: "delegate"`` stub
— rollback is a byte-restore operation, owned by ``re-patch
.restore_original``, not by re-dotnet-patch.

For the byte-splice fallback (the v2.7.0 capability), callers
should continue to use ``re-patch.apply_patch`` directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from re_dotnet_patch import runner


def check_dnlib() -> dict[str, Any]:
    """Probe for the (v2.8.1) Mono.Cecil backend.

    v2.8.1: real probe. Reports ``OK`` when ``patcher-cli`` is
    built and executable; ``WARN`` when only the Python module
    is importable (degraded mode — the runner will return
    "patcher-cli not found" on every call); ``ERROR`` when the
    .NET SDK is missing entirely.
    """
    binary = runner._cli_binary()
    if binary is not None and binary.is_file() and os.access(binary, os.X_OK):
        # Probe the binary itself: ask patcher-cli for its version
        out = runner.run_subcommand("check", timeout_s=10)
        info: dict[str, Any] = {
            "server": "re-dotnet-patch",
            "version": "0.2.0",
            "status": "OK" if out.get("status") == "OK" else "WARN",
            "backend": "mono-cecil-cli-shim",
            "patcher_cli_path": str(binary),
        }
        if "mono_cecil" in out:
            info["mono_cecil_version"] = out["mono_cecil"]
        if "runtime" in out:
            info["dotnet_runtime"] = out["runtime"]
        return info
    return {
        "server": "re-dotnet-patch",
        "version": "0.2.0",
        "status": "WARN",
        "backend": "patcher-cli-not-built",
        "remediation": (
            "Run install.sh — it invokes `dotnet publish` for the "
            "Mono.Cecil backend at "
            "servers/re-dotnet-patch/dotnet/Patcher.Cli/. The "
            "Python MCP server is loadable in degraded mode (the "
            "mutating tools return a structured 'patcher-cli not "
            "found' error)."
        ),
    }


def nop_method(
    path: str, method_fqn: str, dst: str = "", confirm_legal: str = ""
) -> dict[str, Any]:
    """Replace a method body with a NOP-sled, preserving the type graph.

    Args:
        path: source .NET assembly
        method_fqn: e.g. ``"PASystemInfoScanner.MainWindow::GetSteamRegistryKey"``
        dst: destination path for the patched copy (must NOT equal path)
        confirm_legal: audit-trail justification (free-text; not enforced)

    Returns the structured response dict.

    v2.8.1 (C8): the round-trip is now real. Delegates to the
    ``patcher-cli`` Mono.Cecil CLI via
    :func:`re_dotnet_patch.runner.run_subcommand`. The response
    carries the type-graph preservation evidence
    (``type_graph_preserved: bool`` + the per-graph-count
    ``src_X_count`` / ``dst_X_count`` pairs) which the caller
    uses to verify the round-trip is safe.

    CD-3 closure: this is the canonical tool for the r03-stress
    CD patch path (see
    ``See the RE-AI output directory.``
    line 103-114 for the FQNs the patch must target). The
    408 MB ``CrimsonDesert.exe`` binary is the test surface
    (or the real ``MonoLauncher`` if it can be located in the
    install dir).
    """
    src_path = Path(path)
    if not src_path.is_file():
        return {
            "status": "ERROR",
            "error": "src_not_found",
            "path": path,
        }
    if not dst:
        return {
            "status": "ERROR",
            "error": "dst_required",
            "remediation": (
                "Provide a dst path under Output/<run-id>/patches/<target>/ "
                "per the override-scope contract."
            ),
        }
    if Path(dst).resolve() == src_path.resolve():
        return {
            "status": "ERROR",
            "error": "dst_must_differ_from_src",
            "remediation": "re-dotnet-patch is non-destructive; dst != src.",
        }
    out = runner.run_subcommand("nop-method", path, dst, method_fqn)
    if "error" in out:
        return {
            "status": "ERROR",
            "operation": "nop_method",
            "path": path,
            "method_fqn": method_fqn,
            "dst": dst,
            "confirm_legal": confirm_legal,
            "error": out["error"],
            "remediation": (
                "Check that the path is a valid .NET / Mono assembly, "
                "the method FQN is Namespace.Type::Method, and dst is "
                "writable. For Mono assemblies the C# CLI handles the "
                "non-canonical CLI header layout that the lightweight "
                "Python walker misses (A10 fix)."
            ),
        }
    return {
        "status": out.get("status", "ok"),
        "operation": "nop_method",
        "path": path,
        "method_fqn": method_fqn,
        "dst": dst,
        "confirm_legal": confirm_legal,
        "src_sha256": out.get("src_sha256"),
        "dst_sha256": out.get("dst_sha256"),
        "src_type_count": out.get("src_type_count"),
        "dst_type_count": out.get("dst_type_count"),
        "src_method_count": out.get("src_method_count"),
        "dst_method_count": out.get("dst_method_count"),
        "src_field_count": out.get("src_field_count"),
        "dst_field_count": out.get("dst_field_count"),
        "src_property_count": out.get("src_property_count"),
        "dst_property_count": out.get("dst_property_count"),
        "src_event_count": out.get("src_event_count"),
        "dst_event_count": out.get("dst_event_count"),
        "type_graph_preserved": out.get("type_graph_preserved", False),
    }


def replace_method_body(
    path: str, method_fqn: str, new_il_b64: str,
    dst: str = "", confirm_legal: str = "",
) -> dict[str, Any]:
    """Replace a method body with caller-supplied IL bytes.

    v2.8.1 (C8): the round-trip is now real via the ``patcher-cli``
    Mono.Cecil CLI. ``new_il_b64`` is a base64-encoded IL stream
    that the C# side decodes + applies. The v2.8.1 deliverable
    supports two shapes: a single ``ret`` opcode (0x00 0x2A)
    for void returns, and ``ldnull; ret`` (0x02 0x00 0x2A) for
    reference-type returns. Full IL synthesis is v2.9.0.
    """
    if not dst:
        return {
            "status": "ERROR",
            "error": "dst_required",
        }
    out = runner.run_subcommand("replace-method-body", path, dst, method_fqn, new_il_b64)
    if "error" in out:
        return {
            "status": "ERROR",
            "operation": "replace_method_body",
            "path": path,
            "method_fqn": method_fqn,
            "new_il_b64_length": len(new_il_b64),
            "dst": dst,
            "confirm_legal": confirm_legal,
            "error": out["error"],
        }
    return {
        "status": out.get("status", "ok"),
        "operation": "replace_method_body",
        "path": path,
        "method_fqn": method_fqn,
        "new_il_b64_length": len(new_il_b64),
        "dst": dst,
        "confirm_legal": confirm_legal,
        "src_sha256": out.get("src_sha256"),
        "dst_sha256": out.get("dst_sha256"),
        "type_graph_preserved": out.get("type_graph_preserved", False),
    }


def replace_string_ldstr(
    path: str, method_fqn: str, old: str, new: str,
    dst: str = "", confirm_legal: str = "",
) -> dict[str, Any]:
    """Replace a specific ``ldstr`` operand within a method body.

    v2.8.1 (C8): the round-trip is now real via the ``patcher-cli``
    Mono.Cecil CLI. Walks every ``ldstr`` operand in the named
    method (or the whole assembly if ``method_fqn`` is ``"*"``)
    and replaces any operand equal to ``old`` with ``new``.
    """
    if not dst:
        return {
            "status": "ERROR",
            "error": "dst_required",
        }
    out = runner.run_subcommand("replace-string-ldstr", path, dst, method_fqn, old, new)
    if "error" in out:
        return {
            "status": "ERROR",
            "operation": "replace_string_ldstr",
            "path": path,
            "method_fqn": method_fqn,
            "old": old,
            "new": new,
            "dst": dst,
            "confirm_legal": confirm_legal,
            "error": out["error"],
        }
    return {
        "status": out.get("status", "ok"),
        "operation": "replace_string_ldstr",
        "path": path,
        "method_fqn": method_fqn,
        "old": old,
        "new": new,
        "dst": dst,
        "confirm_legal": confirm_legal,
        "replaced": out.get("replaced", 0),
        "src_sha256": out.get("src_sha256"),
        "dst_sha256": out.get("dst_sha256"),
        "type_graph_preserved": out.get("type_graph_preserved", False),
    }


def patch_assembly(
    path: str, operations: list[dict],
    dst: str = "", confirm_legal: str = "",
) -> dict[str, Any]:
    """Apply a list of operations atomically.

    v2.8.1 (C8): writes a temporary ops JSON file (because the
    subprocess argument list isn't a great transport for
    multi-element op descriptors), invokes ``patcher-cli
    patch-assembly`` with the temp file, and surfaces the
    per-op result array.
    """
    if not dst:
        return {
            "status": "ERROR",
            "error": "dst_required",
        }
    import json
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(operations, f)
        ops_path = f.name
    try:
        out = runner.run_subcommand("patch-assembly", path, dst, ops_path)
    finally:
        try:
            import os
            os.unlink(ops_path)
        except OSError:
            pass
    if "error" in out:
        return {
            "status": "ERROR",
            "operation": "patch_assembly",
            "path": path,
            "operation_count": len(operations),
            "operations": operations,
            "dst": dst,
            "confirm_legal": confirm_legal,
            "error": out["error"],
        }
    return {
        "status": out.get("status", "ok"),
        "operation": "patch_assembly",
        "path": path,
        "operation_count": len(operations),
        "operations_applied": out.get("operations_applied"),
        "per_op": out.get("per_op"),
        "dst": dst,
        "confirm_legal": confirm_legal,
        "src_sha256": out.get("src_sha256"),
        "dst_sha256": out.get("dst_sha256"),
        "type_graph_preserved": out.get("type_graph_preserved", False),
    }


def rollback_patch(
    original: str, restore_target: str,
    expected_sha256: str = "", confirm_legal: str = "",
) -> dict[str, Any]:
    """Restore the patched copy to the original via re-patch primitive.

    v2.8.0: delegates to ``re-patch.restore_original`` semantics
    documented under re-patch/. Returns the same structured shape
    as that tool for caller compatibility.

    The delegation is by-documentation; this stub does not import
    re-patch directly to avoid cross-server coupling. Callers should
    call ``re-patch.restore_original`` directly.
    """
    return {
        "status": "delegate",
        "operation": "rollback_patch",
        "original": original,
        "restore_target": restore_target,
        "expected_sha256": expected_sha256,
        "confirm_legal": confirm_legal,
        "remediation": (
            "Call mcp__re-patch__restore_original directly; "
            "re-dotnet-patch does not duplicate the byte-restore "
            "primitive that re-patch already provides."
        ),
    }
