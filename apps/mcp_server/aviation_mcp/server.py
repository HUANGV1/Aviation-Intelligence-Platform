"""Local stdio MCP server exposing aviation operational tools."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp.server.fastmcp import FastMCP

from app.tools.get_international_sigmets import GetInternationalSigmetsTool
from app.tools.get_metar import GetMetarTool
from app.tools.get_notams import GetNotamsTool
from app.tools.get_taf import GetTafTool
from aviation_mcp.adapters import run_tool

mcp = FastMCP("aviation-intelligence")

_metar_tool = GetMetarTool()
_taf_tool = GetTafTool()
_notams_tool = GetNotamsTool()
_sigmets_tool = GetInternationalSigmetsTool()


@mcp.tool()
def get_metar(ids: str) -> dict:
    """Fetch current METAR terminal weather observations for one or more airports.

    Use when the user asks about current winds, visibility, ceilings, or present weather.

    Args:
        ids: One ICAO station or comma-separated list, for example KJFK or KJFK,EGLL.
    """
    return run_tool(_metar_tool, {"ids": ids})


@mcp.tool()
def get_taf(ids: str) -> dict:
    """Fetch terminal aerodrome forecasts (TAF) for one or more airports.

    Use when the user asks about forecast winds, visibility, ceilings, or weather trends.

    Args:
        ids: One ICAO station or comma-separated list, for example KJFK or KJFK,EGLL.
    """
    return run_tool(_taf_tool, {"ids": ids})


@mcp.tool()
def get_notams(icao: str) -> dict:
    """Fetch active NOTAMs for an airport from demo fixture data.

    Returns preloaded demo NOTAM records, not a live NOTAM feed. Use when the user
    asks about runway closures, taxiway restrictions, construction, lighting outages,
    or other published airport notices.

    Args:
        icao: ICAO airport code, for example KJFK or EGLL.
    """
    return run_tool(_notams_tool, {"icao": icao})


@mcp.tool()
def get_international_sigmets(
    hazard: str | None = None,
    level: int | None = None,
    date: str | None = None,
    fir: str | None = None,
) -> dict:
    """Fetch international SIGMET hazard advisories.

    Use when the user asks about enroute or area hazards such as turbulence or icing
    outside domestic US SIGMET coverage.

    Args:
        hazard: Optional hazard filter: turb or ice.
        level: Optional flight level with +/-3000 ft search window.
        date: Optional UTC ISO datetime filter.
        fir: Optional FIR id or name to filter results after retrieval.
    """
    arguments: dict[str, str | int] = {}
    if hazard is not None:
        arguments["hazard"] = hazard
    if level is not None:
        arguments["level"] = level
    if date is not None:
        arguments["date"] = date
    if fir is not None:
        arguments["fir"] = fir
    return run_tool(_sigmets_tool, arguments)


if __name__ == "__main__":
    mcp.run()
