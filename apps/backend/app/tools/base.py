"""Provider-neutral tool contract for the agent layer.

Purpose: Defines typed tool definitions, execution context, and results so internal
tools and future MCP-backed aviation tools can share the same boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class ToolContext:
    """Execution context passed to every tool invocation."""

    document_id: UUID | None = None


@dataclass
class ToolResult:
    """Normalized output from a tool execution."""

    tool_name: str
    success: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata and schema for a registered agent tool."""

    name: str
    description: str
    parameters_schema: dict[str, Any]


class AgentTool(Protocol):
    """Protocol implemented by internal and future MCP-backed tools."""

    definition: ToolDefinition

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult: ...
