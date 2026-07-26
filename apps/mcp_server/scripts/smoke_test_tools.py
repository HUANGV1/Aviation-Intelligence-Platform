"""One-off smoke test for operational MCP tools."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
for path in (BACKEND_DIR, MCP_SERVER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.tools.get_international_sigmets import GetInternationalSigmetsTool
from app.tools.get_metar import GetMetarTool
from app.tools.get_notams import GetNotamsTool
from app.tools.get_taf import GetTafTool
from aviation_mcp.adapters import run_tool

CASES = [
    ("get_metar", GetMetarTool(), {"ids": "KJFK"}),
    ("get_taf", GetTafTool(), {"ids": "KJFK"}),
    ("get_notams", GetNotamsTool(), {"icao": "KJFK"}),
    ("get_international_sigmets", GetInternationalSigmetsTool(), {"hazard": "turb"}),
]

if __name__ == "__main__":
    for name, tool, args in CASES:
        result = run_tool(tool, args)
        source_type = result["operational_source"]["source_type"]
        print(f"{name}: {result['summary']} ({source_type})")
