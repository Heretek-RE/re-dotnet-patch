# re-dotnet-patch

MCP server for structured patching of Mono / .NET assemblies.

## Status

**v2.8.0 — SKELETON.** Tool contracts are final and pinned by tests
(`tests/test_re_dotnet_patch.py`). The actual round-trip patcher
backend (dnlib / Mono.Cecil / pythonnet) lands in v2.8.1.

Every mutating tool currently returns a structured
`{status: "not_implemented", reason, remediation, schema_for_replay}`
dict, so:

1. Downstream skills can target the tool names today.
2. Callers can serialize the operation as a patch descriptor for
   later replay once v2.8.1 lands.
3. The CHANGELOG entry for v2.8.0 can advertise the new server even
   though the backend is deferred.

## Tools

| Tool | Status | What it does |
|---|---|---|
| `check_dnlib` | WARN (stub) | Probe for the future backend |
| `nop_method` | not_implemented | Replace a method body with a NOP-sled (return default) |
| `replace_method_body` | not_implemented | Replace a method body with caller-supplied IL bytes |
| `replace_string_ldstr` | not_implemented | Replace a specific `ldstr` operand within a method body |
| `patch_assembly` | not_implemented | Apply a list of operations atomically |
| `rollback_patch` | delegate | Delegate to `re-patch.restore_original` |

## Why a new server (not a helper in re-patch)?

`re-patch` is byte-splice only, pure-stdlib + mcp/pydantic. Adding a
heavy dnlib / Mono.Cecil dep would bloat re-patch's surface for
callers that only need a byte-splice. Per the v2.8.0 plan
(approved 2026-06-07, LO decision), the Mono dnlib patcher ships as
a new server to keep the dep boundary clean. Costs 1 server-count
entry in `.mcp.json` (30 → 31).

## What this server does NOT do

- It does NOT NOP a method body today. v2.8.1 will. For v2.8.0,
  decompile the assembly with `re-dotnet.decompile_type`, edit the
  C# source by hand to stub the target method, then recompile.
- It does NOT touch native / non-.NET binaries. Use `re-patch` for
  byte-splice; use `re-vm-reverse` for VM-protected native code.
- It does NOT restore originals — call `re-patch.restore_original`
  directly. The `rollback_patch` tool delegates by-documentation.

## Closing CD-3

The r03-stress run identified `MonoLauncher::PASystemInfoScanner.MainWindow`
as the Mono Steam-gate target (see
`See the RE-AI output directory.`
for the full decompile). Once v2.8.1 lands the dnlib backend,
`nop_method("PASystemInfoScanner.MainWindow::GetSteamRegistryKey")`
will close CD-3 as a HIGH-confidence patch (currently DOC-ONLY).

## License

MIT.
