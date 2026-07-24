"""Demo NOTAM provider backed by preloaded fixture data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.operational import OperationalRecord, OperationalSourceBundle
from app.services.operational_normalization import (
    compact_text,
    normalize_location_code,
    parse_iso_datetime,
    utc_now,
)

DEMO_NOTAM_PROVIDER = "demo-notam-api"
DEFAULT_DEMO_NOTAMS_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_notams.json"
NOTAM_TYPE_LABELS = {"N": "new", "R": "replace", "C": "cancel"}


class DemoNotamClient:
    """Server-side demo client that returns customizable preloaded NOTAM records."""

    def __init__(self, *, data_path: Path | str | None = None) -> None:
        self.data_path = Path(data_path) if data_path is not None else DEFAULT_DEMO_NOTAMS_PATH

    def fetch_notams(self, *, icao: str) -> OperationalSourceBundle:
        station = normalize_location_code(icao)
        payload = self._load_station_payload(station)
        items = _extract_notam_items(payload)
        response_icao = str(payload.get("icao") or station).strip().upper()
        total = payload.get("total")
        parsed_total = int(total) if isinstance(total, int) else None
        source_url = f"demo://notams/{response_icao}"
        records = _normalize_notam_records(
            items,
            source_url=source_url,
            location=response_icao,
        )

        pagination: dict[str, Any] = {
            "location": response_icao,
            "count": len(records),
        }
        if parsed_total is not None:
            pagination["total"] = parsed_total

        return OperationalSourceBundle(
            provider=DEMO_NOTAM_PROVIDER,
            source_type="NOTAM",
            source_url=source_url,
            retrieved_at=utc_now(),
            records=records,
            pagination=pagination,
            is_live=False,
        )

    def _load_station_payload(self, station: str) -> dict[str, Any]:
        all_payloads = self._load_all_payloads()
        payload = all_payloads.get(station)
        if isinstance(payload, dict):
            return payload
        return {"icao": station, "notams": [], "total": 0}

    def _load_all_payloads(self) -> dict[str, Any]:
        with self.data_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return {}
        return payload


def _extract_notam_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    notams = payload.get("notams")
    if isinstance(notams, list):
        return [item for item in notams if isinstance(item, dict)]
    return []


def _normalize_notam_records(
    items: list[dict[str, Any]],
    *,
    source_url: str,
    location: str,
) -> list[OperationalRecord]:
    retrieved_at = utc_now()
    records: list[OperationalRecord] = []

    for index, item in enumerate(items):
        notam_id = item.get("notam_id")
        notam_id_domestic = item.get("notam_id_domestic")
        record_key = str(notam_id or notam_id_domestic or f"notam-{index + 1}")
        title = _format_notam_title(item, record_key=record_key)
        summary = _format_notam_summary(item, location=location)
        raw_text = compact_text(item.get("raw"), max_chars=900)

        records.append(
            OperationalRecord(
                record_id=f"notam-{location}-{record_key}-{index}",
                title=title,
                summary=summary,
                source_type="NOTAM",
                provider=DEMO_NOTAM_PROVIDER,
                source_url=source_url,
                retrieved_at=retrieved_at,
                valid_from=parse_iso_datetime(item.get("effective")),
                valid_to=parse_iso_datetime(item.get("expiration")),
                location=str(item.get("location") or location),
                raw_text=raw_text,
                metadata={
                    "notam_id": notam_id,
                    "notam_id_domestic": notam_id_domestic,
                    "type": item.get("type"),
                },
            )
        )

    return records


def _format_notam_title(item: dict[str, Any], *, record_key: str) -> str:
    notam_id = item.get("notam_id")
    if notam_id:
        return f"NOTAM {notam_id}"
    notam_id_domestic = item.get("notam_id_domestic")
    if notam_id_domestic:
        return f"NOTAM {notam_id_domestic}"
    return f"NOTAM {record_key}"


def _format_notam_type_label(notam_type: Any) -> str | None:
    if notam_type is None:
        return None
    code = str(notam_type).strip().upper()
    label = NOTAM_TYPE_LABELS.get(code)
    return f"{code} ({label})" if label else code


def _format_notam_summary(item: dict[str, Any], *, location: str) -> str:
    station = str(item.get("location") or location)
    notam_type = _format_notam_type_label(item.get("type"))
    text = compact_text(item.get("body") or item.get("raw"), max_chars=180)

    parts: list[str] = [station]
    if notam_type:
        parts.append(notam_type)
    if text:
        parts.append(text)

    return ": ".join(parts) if len(parts) > 1 else parts[0]
