"""Normalized schemas for live operational aviation data sources."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OperationalRecord(BaseModel):
    """Compact operational record surfaced to the agent and frontend."""

    record_id: str
    title: str
    summary: str
    source_type: str
    provider: str
    source_url: str
    retrieved_at: datetime
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    location: str | None = None
    raw_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalSourceBundle(BaseModel):
    """Provenance and records returned by an operational API tool."""

    provider: str
    source_type: str
    source_url: str
    retrieved_at: datetime
    records: list[OperationalRecord] = Field(default_factory=list)
    pagination: dict[str, Any] = Field(default_factory=dict)
    is_live: bool = True
