# re-dotnet-patch

MCP server for structured patching of Mono / .NET assemblies: method-body NOP, ldstr replacement, round-trip preservation of the type graph. Closes the gap left by re-patch (byte-splice only).

Version: 0.1.0 | License: MIT

## Structure

```
re-dotnet-patch/
  pyproject.toml                    # build config (setuptools, mcp[cli] + deps)
  src/re_dotnet_patch/
    __init__.py
    __main__.py                     # entry: from server import main; main()
    server.py                       # FastMCP app with @mcp.tool() functions
  README.md
  LICENSE
  SECURITY.md

  bin/                              # CLI scripts
```

## Build

```bash
pip install -e .                    # install with deps
re-dotnet-patch                         # start MCP server on stdio
```



## Tools

This server exposes these MCP tools: `check_dnlib,nop_method,replace_method_body,replace_string_ldstr,patch_assembly,rollback_patch`

## Usage (standalone)

Register this server in your `.mcp.json`:

```json
{
  "mcpServers": {
    "re-dotnet-patch": {
      "command": "uv",
      "args": ["--directory", "/path/to/re-dotnet-patch", "run", "re-dotnet-patch"]
    }
  }
}
```

Or use via the [RE-AI agent-space](https://github.com/Heretek-RE/RE-AI): `./install.sh` clones all servers at pinned versions.
