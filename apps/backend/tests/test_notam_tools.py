"""Tests for demo NOTAM client and tool."""

from pathlib import Path
from unittest.mock import patch

from app.schemas.operational import OperationalRecord, OperationalSourceBundle
from app.services.demo_notam_client import DEMO_NOTAM_PROVIDER, DemoNotamClient
from app.services.operational_normalization import bundle_to_dict, utc_now
from app.tools.base import ToolContext
from app.tools.get_notams import GetNotamsTool


def _sample_notam_bundle() -> OperationalSourceBundle:
    retrieved_at = utc_now()
    return OperationalSourceBundle(
        provider=DEMO_NOTAM_PROVIDER,
        source_type="NOTAM",
        source_url="demo://notams/KJFK",
        retrieved_at=retrieved_at,
        records=[
            OperationalRecord(
                record_id="notam-kjfk-1",
                title="NOTAM A1234/2026",
                summary="KJFK: N (new): RWY 04R/22L CLSD",
                source_type="NOTAM",
                provider=DEMO_NOTAM_PROVIDER,
                source_url="demo://notams/KJFK",
                retrieved_at=retrieved_at,
                location="KJFK",
                raw_text="!KJFK KJFK RWY 04R/22L CLSD 1907001700-1907151700",
            )
        ],
        pagination={"location": "KJFK", "count": 1, "total": 1},
        is_live=False,
    )


def test_demo_notam_client_fetches_preloaded_notams() -> None:
    bundle = DemoNotamClient().fetch_notams(icao="KJFK")

    assert bundle.source_type == "NOTAM"
    assert bundle.provider == DEMO_NOTAM_PROVIDER
    assert bundle.is_live is False
    assert bundle.source_url == "demo://notams/KJFK"
    assert len(bundle.records) == 2
    record = bundle.records[0]
    assert record.location == "KJFK"
    assert record.title == "NOTAM A1234/2026"
    assert "RWY 04R/22L CLSD" in record.summary
    assert record.raw_text == "!KJFK KJFK RWY 04R/22L CLSD 1907001700-1907151700"
    assert record.metadata["notam_id"] == "A1234/2026"
    assert record.metadata["notam_id_domestic"] == "04/323"
    assert record.metadata["type"] == "N"
    assert bundle.pagination["total"] == 2


def test_demo_notam_client_handles_empty_airport() -> None:
    bundle = DemoNotamClient().fetch_notams(icao="KORD")

    assert bundle.records == []
    assert bundle.pagination["count"] == 0
    assert bundle.pagination["total"] == 0
    assert bundle.pagination["location"] == "KORD"


def test_demo_notam_client_prefers_body_for_summary() -> None:
    bundle = DemoNotamClient().fetch_notams(icao="EGLL")

    assert len(bundle.records) == 1
    assert bundle.records[0].location == "EGLL"
    assert "Taxiway A closed for maintenance." in bundle.records[0].summary


def test_demo_notam_client_loads_custom_fixture_file(tmp_path: Path) -> None:
    fixture_path = tmp_path / "demo_notams.json"
    fixture_path.write_text(
        """
        {
          "KSEA": {
            "icao": "KSEA",
            "notams": [
              {
                "raw": "!KSEA KSEA RWY 16C/34C CLSD",
                "notam_id": "D1111/2026",
                "location": "KSEA",
                "body": "Runway 16C/34C closed overnight."
              }
            ],
            "total": 1
          }
        }
        """,
        encoding="utf-8",
    )

    bundle = DemoNotamClient(data_path=fixture_path).fetch_notams(icao="KSEA")

    assert len(bundle.records) == 1
    assert bundle.records[0].title == "NOTAM D1111/2026"
    assert "Runway 16C/34C closed overnight." in bundle.records[0].summary


def test_get_notams_tool_validates_icao() -> None:
    tool = GetNotamsTool()
    result = tool.execute({"icao": ""}, ToolContext())

    assert result.success is False
    assert "icao" in (result.error or "").lower() or "location" in (result.error or "").lower()


@patch("app.tools.get_notams.DemoNotamClient.fetch_notams")
def test_get_notams_tool_success(mock_fetch) -> None:
    mock_fetch.return_value = _sample_notam_bundle()

    tool = GetNotamsTool()
    result = tool.execute({"icao": "KJFK"}, ToolContext())

    assert result.success is True
    assert "NOTAM" in result.summary
    assert "operational_source" in result.data
    assert bundle_to_dict(_sample_notam_bundle())["source_type"] == "NOTAM"


@patch("app.tools.get_notams.DemoNotamClient.fetch_notams")
def test_get_notams_tool_maps_client_error(mock_fetch) -> None:
    from app.services.operational_http import OperationalAPIError

    mock_fetch.side_effect = OperationalAPIError("Demo NOTAM lookup failed.")

    tool = GetNotamsTool()
    result = tool.execute({"icao": "KJFK"}, ToolContext())

    assert result.success is False
    assert "Demo NOTAM lookup failed." in (result.error or "")


def test_get_notams_tool_end_to_end_with_fixture_data() -> None:
    tool = GetNotamsTool()
    result = tool.execute({"icao": "KLAX"}, ToolContext())

    assert result.success is True
    assert "1 active NOTAM" in result.summary
    operational_source = result.data["operational_source"]
    assert operational_source["provider"] == DEMO_NOTAM_PROVIDER
    assert operational_source["is_live"] is False
    assert len(operational_source["records"]) == 1
