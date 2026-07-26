# Aviation Intelligence MCP Server

Local [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes aviation operational tools to Cursor, Claude Desktop, Claude Code, and other MCP-compatible clients.

The server reuses the same tool classes as the FastAPI backend agent (`GetMetarTool`, `GetTafTool`, `GetNotamsTool`, `GetInternationalSigmetsTool`) via direct in-process import. No backend process needs to be running.

## Tools

| Tool | Description |
| --- | --- |
| `get_metar` | Current METAR observations from AviationWeather.gov |
| `get_taf` | Terminal aerodrome forecasts from AviationWeather.gov |
| `get_notams` | Demo/fixture NOTAM data (not a live feed) |
| `get_international_sigmets` | International SIGMET advisories from AviationWeather.gov |

Document search and RAG tools are intentionally excluded from this MCP server.

## Setup

From the repository root:

```bash
cd apps/mcp_server
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

No `DATABASE_URL` or `GEMINI_API_KEY` is required for the operational tools.

## Run standalone

```bash
cd apps/mcp_server
python -m aviation_mcp.server
```

The server communicates over stdio and is meant to be launched by an MCP client, not run interactively.

## Client configuration

Use the same server command in each client. Only the config file location differs.

Point `command` at the project venv Python (system `python` will not have `mcp` installed or find the package). Set `PYTHONPATH` to `apps/mcp_server` so `-m aviation_mcp.server` resolves without relying on `cwd`.

### Cursor

This repo includes [`.cursor/mcp.json`](../../.cursor/mcp.json) at the project root:

```json
{
  "mcpServers": {
    "aviation": {
      "command": "${workspaceFolder}/apps/mcp_server/.venv/Scripts/python.exe",
      "args": ["-m", "aviation_mcp.server"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/apps/mcp_server"
      }
    }
  }
}
```

On macOS/Linux, use `.venv/bin/python` instead of `.venv/Scripts/python.exe`.

After changing the config, restart the MCP server from **Settings → MCP** (or reload Cursor). Confirm the `aviation` server shows four tools.

### Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS:

```json
{
  "mcpServers": {
    "aviation": {
      "command": "C:/Users/you/Coding Projects/Aviation-Intelligence-Platform/apps/mcp_server/.venv/Scripts/python.exe",
      "args": ["-m", "aviation_mcp.server"],
      "env": {
        "PYTHONPATH": "C:/Users/you/Coding Projects/Aviation-Intelligence-Platform/apps/mcp_server"
      }
    }
  }
}
```

Use absolute paths to your clone and venv Python.

### Claude Code

CLI:

```bash
claude mcp add aviation -- python -m aviation_mcp.server
```

Or add a project `.mcp.json` with the same `mcpServers` shape as Cursor.

## Smoke test with MCP Inspector

```bash
cd apps/mcp_server
npx @modelcontextprotocol/inspector python -m aviation_mcp.server
```

Call each tool once:

- `get_metar` with `ids: "KJFK"`
- `get_taf` with `ids: "KJFK"`
- `get_notams` with `icao: "KJFK"`
- `get_international_sigmets` with no args or `hazard: "turb"`

Or run the bundled script (no Inspector required):

```bash
cd apps/mcp_server
python scripts/smoke_test_tools.py
```

## Tests

```bash
cd apps/mcp_server
pytest tests/
```

## Architecture

```text
Cursor / Claude / other MCP client
  -> stdio JSON-RPC
  -> apps/mcp_server/aviation_mcp/server.py
  -> aviation_mcp/adapters.py
  -> apps/backend/app/tools/* (same classes as the web agent)
  -> AviationWeather.gov / demo NOTAM fixtures
```

The FastAPI backend and web agent are unchanged. This MCP server is a thin outward-facing adapter.
