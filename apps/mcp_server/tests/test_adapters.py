"""Unit tests for MCP adapter helpers."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
for path in (BACKEND_DIR, MCP_SERVER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pytest

from app.tools.base import ToolContext, ToolDefinition, ToolResult
from aviation_mcp.adapters import ToolExecutionError, run_tool, tool_result_to_payload


class _FakeTool:
    definition = ToolDefinition(
        name="fake_tool",
        description="Fake tool for adapter tests.",
        parameters_schema={"type": "object", "properties": {}},
    )

    def __init__(self, result: ToolResult) -> None:
        self._result = result
        self.last_arguments: dict | None = None

    def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
        self.last_arguments = arguments
        del context
        return self._result


def test_tool_result_to_payload_success() -> None:
    payload = tool_result_to_payload(
        ToolResult(
            tool_name="get_metar",
            success=True,
            summary="Retrieved 1 current METAR.",
            data={"operational_source": {"source_type": "METAR"}},
        )
    )

    assert payload == {
        "summary": "Retrieved 1 current METAR.",
        "operational_source": {"source_type": "METAR"},
    }


def test_tool_result_to_payload_failure_prefers_error_message() -> None:
    with pytest.raises(ToolExecutionError, match="Invalid station id"):
        tool_result_to_payload(
            ToolResult(
                tool_name="get_metar",
                success=False,
                summary="METAR lookup failed.",
                error="Invalid station id",
            )
        )


def test_tool_result_to_payload_failure_falls_back_to_summary() -> None:
    with pytest.raises(ToolExecutionError, match="METAR lookup failed."):
        tool_result_to_payload(
            ToolResult(
                tool_name="get_metar",
                success=False,
                summary="METAR lookup failed.",
            )
        )


def test_run_tool_executes_with_empty_context() -> None:
    tool = _FakeTool(
        ToolResult(
            tool_name="get_taf",
            success=True,
            summary="Retrieved 1 TAF.",
            data={"operational_source": {"source_type": "TAF"}},
        )
    )

    payload = run_tool(tool, {"ids": "KJFK"})

    assert tool.last_arguments == {"ids": "KJFK"}
    assert payload["summary"] == "Retrieved 1 TAF."
    assert payload["operational_source"]["source_type"] == "TAF"
