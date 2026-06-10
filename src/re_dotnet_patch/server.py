"""MCP server entry point for re-dotnet-patch.

v2.8.0 ships the SERVER SKELETON: tool contracts are final and pinned
by tests; the round-trip patcher backend (dnlib / Mono.Cecil /
pythonnet) lands in v2.8.1.

See patcher.py for the operation semantics.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from re_dotnet_patch import patcher

logger = logging.getLogger("re_dotnet_patch")
logger.setLevel(logging.INFO)

mcp = FastMCP("re-dotnet-patch")


@mcp.tool()
def check_dnlib() -> dict:
    """Probe for the dnlib / Mono.Cecil backend.

    v2.8.0: always returns ``status: WARN`` (stub backend). v2.8.1
    replaces this with a real backend probe.
    """
    return patcher.check_dnlib()


@mcp.tool()
def nop_method(
    path: str, method_fqn: str, dst: str = "", confirm_legal: str = ""
) -> dict:
    """Replace a method body with a NOP-sled (return default).

    The patched copy is written to *dst* (must differ from *path*);
    the original is never modified. The round-trip preserves the
    type graph outside the NOPed method (counts of types / methods /
    fields / properties / events all unchanged).

    Args:
        path: source .NET assembly
        method_fqn: e.g. ``"Namespace.Type::Method"``
        dst: destination path for the patched copy
        confirm_legal: free-text audit-trail justification

    Use case: stub a store-gate / license-gate / telemetry-gate method
    in a Mono / .NET launcher. Closes the CD-3 patch path (see
    See the RE-AI output directory.
    MainWindow.cs for the canonical example).

    v2.8.0: returns ``status: not_implemented`` with a schema_for_replay
    descriptor; v2.8.1 lands the round-trip backend.
    """
    return patcher.nop_method(path, method_fqn, dst, confirm_legal)


@mcp.tool()
def replace_method_body(
    path: str, method_fqn: str, new_il_b64: str,
    dst: str = "", confirm_legal: str = "",
) -> dict:
    """Replace a method body with caller-supplied IL bytes.

    v2.8.0: returns ``status: not_implemented``.
    """
    return patcher.replace_method_body(
        path, method_fqn, new_il_b64, dst, confirm_legal
    )


@mcp.tool()
def replace_string_ldstr(
    path: str, method_fqn: str, old: str, new: str,
    dst: str = "", confirm_legal: str = "",
) -> dict:
    """Replace a specific ``ldstr`` operand within a method body.

    v2.8.0: returns ``status: not_implemented``.
    """
    return patcher.replace_string_ldstr(
        path, method_fqn, old, new, dst, confirm_legal
    )


@mcp.tool()
def patch_assembly(
    path: str, operations: list[dict],
    dst: str = "", confirm_legal: str = "",
) -> dict:
    """Apply a list of operations atomically.

    v2.8.0: returns ``status: not_implemented``.
    """
    return patcher.patch_assembly(path, operations, dst, confirm_legal)


@mcp.tool()
def rollback_patch(
    original: str, restore_target: str,
    expected_sha256: str = "", confirm_legal: str = "",
) -> dict:
    """Delegate to re-patch.restore_original for the byte-restore step.

    re-dotnet-patch does not duplicate the byte-level restore primitive;
    this stub returns ``status: delegate`` with a remediation hint
    pointing at re-patch.restore_original.
    """
    return patcher.rollback_patch(
        original, restore_target, expected_sha256, confirm_legal
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
