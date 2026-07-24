"""NOTAM lookup tool backed by the demo NOTAM provider."""

from __future__ import annotations

from typing import Any

from app.schemas.operational import OperationalSourceBundle
from app.services.demo_notam_client import DemoNotamClient
from app.services.operational_http import OperationalAPIError
from app.services.operational_normalization import bundle_to_dict, normalize_location_code
from app.tools.base import ToolContext, ToolDefinition, ToolResult

GET_NOTAMS_TOOL_NAME = "get_notams"

GET_NOTAMS_DEFINITION = ToolDefinition(
    name=GET_NOTAMS_TOOL_NAME,
    description=(
        "Fetch active NOTAMs for an airport. Use when the user asks about runway closures, "
        "taxiway restrictions, construction, lighting outages, or other published airport notices."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "icao": {
                "type": "string",
                "description": "ICAO airport code, for example KJFK or EGLL.",
            },
        },
        "required": ["icao"],
    },
)


def _build_summary(bundle: OperationalSourceBundle) -> str:
    count = len(bundle.records)
    location = bundle.pagination.get("location")
    if count == 0:
        if location:
            return f"No NOTAMs were returned for {location}."
        return "No NOTAMs were returned for the requested airport."
    label = "NOTAM" if count == 1 else "NOTAMs"
    if location:
        return f"Retrieved {count} active {label} for {location}."
    return f"Retrieved {count} active {label}."


class GetNotamsTool:
    definition = GET_NOTAMS_DEFINITION

    def __init__(self, client: DemoNotamClient | None = None) -> None:
        self._client = client or DemoNotamClient()

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        try:
            icao = normalize_location_code(str(arguments.get("icao", "")))
            bundle = self._client.fetch_notams(icao=icao)
        except (OperationalAPIError, ValueError) as exc:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                summary="NOTAM lookup failed.",
                error=str(exc),
            )

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            summary=_build_summary(bundle),
            data={"operational_source": bundle_to_dict(bundle)},
        )
