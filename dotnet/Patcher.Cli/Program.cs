// patcher-cli: Mono.Cecil-backed round-trip patcher for Mono / .NET
// assemblies. v2.8.1 (C8) backend for the re-dotnet-patch MCP server.
//
// Subcommand surface (one JSON document on stdout per invocation):
//   nop-method          <src> <dst> <method_fqn>
//   replace-method-body <src> <dst> <method_fqn> <new_il_b64>
//   replace-string-ldstr <src> <dst> <method_fqn> <old> <new>
//   patch-assembly      <src> <dst> <ops_json_path>
//   check
//
// The Python MCP server (re-dotnet-patch.runner) locates this binary
// via the RE_DOTNET_PATCH_CLI_PATH env var (or the
// <server>/bin/patcher-cli default), invokes one subcommand per
// request, parses the JSON response, and verifies the type-graph
// preservation contract by re-calling re-dotnet-cli list-types on
// the patched copy.
//
// Type-graph preservation (src.X_count == dst.X_count for types /
// methods / fields / properties / events) is the proof of
// round-trip safety. Byte-identity is NOT required — Mono.Cecil
// rewrites PE headers, image sizes, and the #US heap on Write,
// but the ECMA-335 type/method/field/property/event tables are
// preserved.
//
// Vendor-neutral: Mono.Cecil is a library, not a product. The
// subcommand names are generic. No obfuscation product is named.

using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;
using Re.Dotnet.Patch.Cli;

var subcommand = args.Length > 0 ? args[0] : "check";
var writer = new OutputWriter();

try
{
    switch (subcommand)
    {
        case "check":
            writer.Write(new
            {
                status = "OK",
                mono_cecil = typeof(Mono.Cecil.AssemblyDefinition).Assembly.GetName().Version?.ToString() ?? "unknown",
                runtime = System.Environment.Version.ToString(),
            });
            break;
        case "nop-method":
            RequireArg(args, 3, "nop-method <src> <dst> <method_fqn>");
            writer.Write(Patcher.NopMethod(args[1], args[2], args[3]));
            break;
        case "replace-method-body":
            RequireArg(args, 4, "replace-method-body <src> <dst> <method_fqn> <new_il_b64>");
            writer.Write(Patcher.ReplaceMethodBody(args[1], args[2], args[3], args[4]));
            break;
        case "replace-string-ldstr":
            RequireArg(args, 5, "replace-string-ldstr <src> <dst> <method_fqn> <old> <new>");
            writer.Write(Patcher.ReplaceStringLdstr(args[1], args[2], args[3], args[4], args[5]));
            break;
        case "patch-assembly":
            RequireArg(args, 3, "patch-assembly <src> <dst> <ops_json_path>");
            writer.Write(Patcher.PatchAssembly(args[1], args[2], args[3]));
            break;
        default:
            writer.WriteError($"unknown subcommand: {subcommand}");
            return 2;
    }
    return 0;
}
catch (Exception ex)
{
    writer.WriteError(ex.ToString());
    return 1;
}

static void RequireArg(string[] argv, int index, string usage)
{
    if (argv.Length <= index)
    {
        throw new ArgumentException($"missing required argument: {usage}");
    }
}

internal sealed class OutputWriter
{
    private static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    public void Write(object payload)
    {
        Console.Out.WriteLine(JsonSerializer.Serialize(payload, Options));
    }

    public void WriteError(string message)
    {
        Console.Error.WriteLine(JsonSerializer.Serialize(new { error = message }, Options));
    }
}
