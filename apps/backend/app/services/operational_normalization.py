"""Helpers for normalizing operational API payloads into agent-facing records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_location_code(value: str) -> str:
    code = value.strip().upper()
    if not code:
        raise ValueError("location is required.")
    if len(code) < 3 or len(code) > 4:
        raise ValueError("location must be a 3 or 4 character ICAO/FAA code.")
    if not code.isalnum():
        raise ValueError("location must contain only letters and numbers.")
    return code


def normalize_station_ids(value: Any) -> list[str]:
    if value is None:
        raise ValueError("ids is required.")
    if isinstance(value, str):
        raw_items = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        raw_items = [str(item).strip() for item in value]
    else:
        raise ValueError("ids must be a string or list of station identifiers.")

    ids = [normalize_location_code(item) for item in raw_items if item]
    if not ids:
        raise ValueError("ids must include at least one station identifier.")
    if len(ids) > 5:
        raise ValueError("ids supports up to 5 station identifiers per request.")
    return ids


def bundle_to_dict(bundle: Any) -> dict[str, Any]:
    return bundle.model_dump(mode="json")


def compact_text(value: Any, *, max_chars: int = 500) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}..."
