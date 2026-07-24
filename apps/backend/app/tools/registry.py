"""Registry of tools available to the agent orchestrator."""

from __future__ import annotations

from app.tools.base import AgentTool, ToolDefinition


class ToolRegistry:
    """In-memory registry for agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.definition.name] = tool

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def list_definitions(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())


_default_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Return the process-wide tool registry, initializing defaults on first use."""
    global _default_registry
    if _default_registry is None:
        from app.tools.document_search import DocumentSearchTool
        from app.tools.get_international_sigmets import GetInternationalSigmetsTool
        from app.tools.get_metar import GetMetarTool
        from app.tools.get_notams import GetNotamsTool
        from app.tools.get_taf import GetTafTool

        registry = ToolRegistry()
        registry.register(DocumentSearchTool())
        registry.register(GetMetarTool())
        registry.register(GetNotamsTool())
        registry.register(GetTafTool())
        registry.register(GetInternationalSigmetsTool())
        _default_registry = registry
    return _default_registry
