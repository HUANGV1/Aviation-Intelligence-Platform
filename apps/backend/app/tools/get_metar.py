"""METAR lookup tool backed by AviationWeather.gov."""

from __future__ import annotations

from typing import Any

from app.schemas.operational import OperationalSourceBundle
from app.services.aviation_weather_client import AviationWeatherClient
from app.services.operational_http import OperationalAPIError
from app.services.operational_normalization import bundle_to_dict, normalize_station_ids
from app.tools.base import ToolContext, ToolDefinition, ToolResult

GET_METAR_TOOL_NAME = "get_metar"

GET_METAR_DEFINITION = ToolDefinition(
    name=GET_METAR_TOOL_NAME,
    description=(
        "Fetch current METAR terminal weather observations for one or more airports. "
        "Use when the user asks about current winds, visibility, ceilings, or present weather."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "ids": {
                "type": "string",
                "description": "One ICAO station or comma-separated list, for example KJFK or KJFK,EGLL.",
            },
        },
        "required": ["ids"],
    },
)


def _build_summary(bundle: OperationalSourceBundle) -> str:
    count = len(bundle.records)
    if count == 0:
        return "No METAR observations were returned for the requested stations."
    label = "METAR" if count == 1 else "METARs"
    return f"Retrieved {count} current {label}."


class GetMetarTool:
    definition = GET_METAR_DEFINITION

    def __init__(self, client: AviationWeatherClient | None = None) -> None:
        self._client = client or AviationWeatherClient()

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        try:
            station_ids = normalize_station_ids(arguments.get("ids"))
            bundle = self._client.fetch_metar(ids=station_ids)
        except (OperationalAPIError, ValueError) as exc:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                summary="METAR lookup failed.",
                error=str(exc),
            )

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            summary=_build_summary(bundle),
            data={"operational_source": bundle_to_dict(bundle)},
        )
