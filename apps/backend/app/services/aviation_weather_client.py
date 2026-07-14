"""AviationWeather.gov API client for METAR, TAF, and international SIGMETs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from app.config import settings
from app.schemas.operational import OperationalRecord, OperationalSourceBundle
from app.services.operational_http import OperationalAPIError, request_json
from app.services.operational_normalization import (
    compact_text,
    normalize_station_ids,
    parse_iso_datetime,
    utc_now,
)

AVIATION_WEATHER_PROVIDER = "aviationweather.gov"
VALID_ISIGMET_HAZARDS = {"turb", "ice"}


class AviationWeatherClient:
    """Server-side client for public AviationWeather.gov data endpoints."""

    def __init__(self, *, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.aviation_weather_base_url).rstrip("/")

    def fetch_metar(self, *, ids: str | list[str]) -> OperationalSourceBundle:
        station_ids = normalize_station_ids(ids)
        params = {"ids": ",".join(station_ids), "format": "json"}
        return self._fetch_station_products(
            endpoint="metar",
            params=params,
            source_type="METAR",
            station_ids=station_ids,
        )

    def fetch_taf(self, *, ids: str | list[str]) -> OperationalSourceBundle:
        station_ids = normalize_station_ids(ids)
        params = {"ids": ",".join(station_ids), "format": "json"}
        return self._fetch_station_products(
            endpoint="taf",
            params=params,
            source_type="TAF",
            station_ids=station_ids,
        )

    def fetch_international_sigmets(
        self,
        *,
        hazard: str | None = None,
        level: int | None = None,
        date: str | None = None,
        fir: str | None = None,
    ) -> OperationalSourceBundle:
        params: dict[str, str] = {"format": "json"}
        if hazard:
            normalized_hazard = hazard.strip().lower()
            if normalized_hazard not in VALID_ISIGMET_HAZARDS:
                raise OperationalAPIError("hazard must be one of: turb, ice.")
            params["hazard"] = normalized_hazard
        if level is not None:
            if level < 0:
                raise OperationalAPIError("level must be a non-negative integer.")
            params["level"] = str(level)
        if date:
            params["date"] = date.strip()

        payload, source_url = self._request("isigmet", params)
        items = _ensure_list(payload)
        records = _normalize_sigmet_records(items, source_url=source_url)

        if fir:
            normalized_fir = fir.strip().upper()
            records = [
                record
                for record in records
                if (record.metadata.get("fir_id") or "").upper() == normalized_fir
                or (record.metadata.get("fir_name") or "").upper() == normalized_fir
            ]

        return OperationalSourceBundle(
            provider=AVIATION_WEATHER_PROVIDER,
            source_type="SIGMET",
            source_url=source_url,
            retrieved_at=utc_now(),
            records=records,
            pagination={"count": len(records)},
            is_live=True,
        )

    def _fetch_station_products(
        self,
        *,
        endpoint: str,
        params: dict[str, str],
        source_type: str,
        station_ids: list[str],
    ) -> OperationalSourceBundle:
        payload, source_url = self._request(endpoint, params)
        items = _ensure_list(payload)
        records = _normalize_station_records(
            items,
            source_type=source_type,
            source_url=source_url,
        )
        return OperationalSourceBundle(
            provider=AVIATION_WEATHER_PROVIDER,
            source_type=source_type,
            source_url=source_url,
            retrieved_at=utc_now(),
            records=records,
            pagination={"ids": station_ids, "count": len(records)},
            is_live=True,
        )

    def _request(self, endpoint: str, params: dict[str, str]) -> tuple[Any, str]:
        query = urlencode(params)
        url = f"{self.base_url}/api/data/{endpoint}?{query}"
        return request_json("GET", url)


def _ensure_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    return []


def _normalize_station_records(
    items: list[dict[str, Any]],
    *,
    source_type: str,
    source_url: str,
) -> list[OperationalRecord]:
    retrieved_at = utc_now()
    records: list[OperationalRecord] = []

    for index, item in enumerate(items):
        station = str(item.get("icaoId") or item.get("stationId") or f"station-{index + 1}")
        if source_type == "METAR":
            summary = _format_metar_summary(item)
            observed_at = parse_iso_datetime(item.get("obsTime") or item.get("reportTime"))
            raw_text = compact_text(item.get("rawOb"), max_chars=500)
        else:
            summary = _format_taf_summary(item)
            observed_at = parse_iso_datetime(item.get("issueTime") or item.get("bulletinTime"))
            raw_text = compact_text(item.get("rawTAF"), max_chars=900)

        records.append(
            OperationalRecord(
                record_id=f"{source_type.lower()}-{station}-{index}",
                title=f"{source_type} {station}",
                summary=summary,
                source_type=source_type,
                provider=AVIATION_WEATHER_PROVIDER,
                source_url=source_url,
                retrieved_at=retrieved_at,
                observed_at=observed_at,
                valid_from=parse_iso_datetime(item.get("validTimeFrom")),
                valid_to=parse_iso_datetime(item.get("validTimeTo")),
                location=station,
                raw_text=raw_text,
                metadata={
                    "name": item.get("name"),
                    "flt_cat": item.get("fltCat"),
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                },
            )
        )

    return records


def _normalize_sigmet_records(
    items: list[dict[str, Any]],
    *,
    source_url: str,
) -> list[OperationalRecord]:
    retrieved_at = utc_now()
    records: list[OperationalRecord] = []

    for index, item in enumerate(items):
        hazard = str(item.get("hazard") or "SIGMET")
        fir_name = str(item.get("firName") or item.get("firId") or "International")
        series = str(item.get("seriesId") or f"SIGMET-{index + 1}")
        summary = f"{hazard} SIGMET for {fir_name}"
        if item.get("qualifier"):
            summary = f"{summary} ({item['qualifier']})"

        records.append(
            OperationalRecord(
                record_id=f"sigmet-{series}-{index}",
                title=series,
                summary=summary,
                source_type="SIGMET",
                provider=AVIATION_WEATHER_PROVIDER,
                source_url=source_url,
                retrieved_at=retrieved_at,
                valid_from=parse_iso_datetime(item.get("validTimeFrom")),
                valid_to=parse_iso_datetime(item.get("validTimeTo")),
                location=fir_name,
                raw_text=compact_text(item.get("rawSigmet"), max_chars=900),
                metadata={
                    "hazard": item.get("hazard"),
                    "qualifier": item.get("qualifier"),
                    "base": item.get("base"),
                    "top": item.get("top"),
                    "fir_id": item.get("firId"),
                    "fir_name": item.get("firName"),
                    "dir": item.get("dir"),
                    "spd": item.get("spd"),
                },
            )
        )

    return records


def _format_metar_summary(item: dict[str, Any]) -> str:
    parts: list[str] = []
    station = item.get("icaoId") or "station"
    parts.append(str(station))
    if item.get("fltCat"):
        parts.append(f"flight category {item['fltCat']}")
    if item.get("wdir") is not None and item.get("wspd") is not None:
        parts.append(f"wind {item['wdir']} at {item['wspd']} kt")
    if item.get("visib") is not None:
        parts.append(f"visibility {item['visib']} sm")
    if item.get("wxString"):
        parts.append(str(item["wxString"]))
    return ", ".join(parts)


def _format_taf_summary(item: dict[str, Any]) -> str:
    station = item.get("icaoId") or "station"
    raw = compact_text(item.get("rawTAF"), max_chars=180)
    if raw:
        return f"{station}: {raw}"
    return f"TAF available for {station}"
