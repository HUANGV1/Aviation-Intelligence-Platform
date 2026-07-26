"""Bridge AgentTool execution results to MCP tool responses."""

from __future__ import annotations

from typing import Any

from app.tools.base import AgentTool, ToolContext, ToolResult


class ToolExecutionError(Exception):
    """Raised when an underlying agent tool returns a failure result."""


def run_tool(tool: AgentTool, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute an agent tool and return a JSON-serializable MCP payload."""
    result = tool.execute(arguments, ToolContext())
    return tool_result_to_payload(result)


def tool_result_to_payload(result: ToolResult) -> dict[str, Any]:
    """Convert a ToolResult into the MCP tool response shape."""
    if not result.success:
        raise ToolExecutionError(result.error or result.summary)
    return {"summary": result.summary, **result.data}
