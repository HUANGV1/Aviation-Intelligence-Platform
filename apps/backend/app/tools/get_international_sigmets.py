"""International SIGMET lookup tool backed by AviationWeather.gov."""

from __future__ import annotations

from typing import Any

from app.schemas.operational import OperationalSourceBundle
from app.services.aviation_weather_client import AviationWeatherClient
from app.services.operational_http import OperationalAPIError
from app.services.operational_normalization import bundle_to_dict
from app.tools.base import ToolContext, ToolDefinition, ToolResult

GET_INTERNATIONAL_SIGMETS_TOOL_NAME = "get_international_sigmets"

GET_INTERNATIONAL_SIGMETS_DEFINITION = ToolDefinition(
    name=GET_INTERNATIONAL_SIGMETS_TOOL_NAME,
    description=(
        "Fetch international SIGMET hazard advisories. Use when the user asks about "
        "enroute or area hazards such as turbulence or icing outside domestic US SIGMET coverage."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "hazard": {
                "type": "string",
                "description": "Optional hazard filter: turb or ice.",
            },
            "level": {
                "type": "integer",
                "description": "Optional flight level with +/-3000 ft search window.",
            },
            "date": {
                "type": "string",
                "description": "Optional UTC ISO datetime filter.",
            },
            "fir": {
                "type": "string",
                "description": "Optional FIR id or name to filter results after retrieval.",
            },
        },
    },
)


def _build_summary(bundle: OperationalSourceBundle) -> str:
    count = len(bundle.records)
    if count == 0:
        return "No international SIGMETs matched the requested filters."
    label = "SIGMET" if count == 1 else "SIGMETs"
    return f"Retrieved {count} international {label}."


class GetInternationalSigmetsTool:
    definition = GET_INTERNATIONAL_SIGMETS_DEFINITION

    def __init__(self, client: AviationWeatherClient | None = None) -> None:
        self._client = client or AviationWeatherClient()

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        hazard = arguments.get("hazard")
        level = arguments.get("level")
        date = arguments.get("date")
        fir = arguments.get("fir")

        try:
            parsed_level = int(level) if level is not None else None
            bundle = self._client.fetch_international_sigmets(
                hazard=str(hazard) if hazard else None,
                level=parsed_level,
                date=str(date) if date else None,
                fir=str(fir) if fir else None,
            )
        except (OperationalAPIError, ValueError, TypeError) as exc:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                summary="International SIGMET lookup failed.",
                error=str(exc),
            )

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            summary=_build_summary(bundle),
            data={"operational_source": bundle_to_dict(bundle)},
        )
