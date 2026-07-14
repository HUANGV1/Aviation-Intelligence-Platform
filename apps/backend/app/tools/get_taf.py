"""TAF lookup tool backed by AviationWeather.gov."""

from __future__ import annotations

from typing import Any

from app.schemas.operational import OperationalSourceBundle
from app.services.aviation_weather_client import AviationWeatherClient
from app.services.operational_http import OperationalAPIError
from app.services.operational_normalization import bundle_to_dict, normalize_station_ids
from app.tools.base import ToolContext, ToolDefinition, ToolResult

GET_TAF_TOOL_NAME = "get_taf"

GET_TAF_DEFINITION = ToolDefinition(
    name=GET_TAF_TOOL_NAME,
    description=(
        "Fetch terminal aerodrome forecasts (TAF) for one or more airports. "
        "Use when the user asks about forecast winds, visibility, ceilings, or weather trends."
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
        return "No TAF forecasts were returned for the requested stations."
    label = "TAF" if count == 1 else "TAFs"
    return f"Retrieved {count} {label}."


class GetTafTool:
    definition = GET_TAF_DEFINITION

    def __init__(self, client: AviationWeatherClient | None = None) -> None:
        self._client = client or AviationWeatherClient()

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        try:
            station_ids = normalize_station_ids(arguments.get("ids"))
            bundle = self._client.fetch_taf(ids=station_ids)
        except (OperationalAPIError, ValueError) as exc:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                summary="TAF lookup failed.",
                error=str(exc),
            )

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            summary=_build_summary(bundle),
            data={"operational_source": bundle_to_dict(bundle)},
        )
