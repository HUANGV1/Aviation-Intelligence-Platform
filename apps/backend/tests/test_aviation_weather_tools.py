"""Tests for AviationWeather.gov clients and tools."""

from unittest.mock import patch

from app.schemas.operational import OperationalRecord, OperationalSourceBundle
from app.services.aviation_weather_client import AviationWeatherClient
from app.services.operational_normalization import bundle_to_dict, utc_now
from app.tools.base import ToolContext
from app.tools.get_international_sigmets import GetInternationalSigmetsTool
from app.tools.get_metar import GetMetarTool
from app.tools.get_taf import GetTafTool


def _sample_metar_bundle() -> OperationalSourceBundle:
    retrieved_at = utc_now()
    return OperationalSourceBundle(
        provider="aviationweather.gov",
        source_type="METAR",
        source_url="https://aviationweather.gov/api/data/metar?ids=KJFK&format=json",
        retrieved_at=retrieved_at,
        records=[
            OperationalRecord(
                record_id="metar-kjfk",
                title="METAR KJFK",
                summary="KJFK, flight category VFR",
                source_type="METAR",
                provider="aviationweather.gov",
                source_url="https://aviationweather.gov/api/data/metar?ids=KJFK&format=json",
                retrieved_at=retrieved_at,
                location="KJFK",
                raw_text="KJFK 032151Z 23006KT 10SM BKN110 14/03 A3000",
            )
        ],
        pagination={"count": 1, "ids": "KJFK"},
    )


def _sample_taf_bundle() -> OperationalSourceBundle:
    retrieved_at = utc_now()
    return OperationalSourceBundle(
        provider="aviationweather.gov",
        source_type="TAF",
        source_url="https://aviationweather.gov/api/data/taf?ids=KJFK&format=json",
        retrieved_at=retrieved_at,
        records=[
            OperationalRecord(
                record_id="taf-kjfk",
                title="TAF KJFK",
                summary="KJFK terminal forecast issued",
                source_type="TAF",
                provider="aviationweather.gov",
                source_url="https://aviationweather.gov/api/data/taf?ids=KJFK&format=json",
                retrieved_at=retrieved_at,
                location="KJFK",
                raw_text="KJFK 032320Z 0400/0506 VRB05KT P6SM FEW050",
            )
        ],
        pagination={"count": 1, "ids": "KJFK"},
    )


@patch("app.services.aviation_weather_client.request_json")
def test_aviation_weather_client_fetches_metar(mock_request) -> None:
    mock_request.return_value = (
        [
            {
                "icaoId": "KJFK",
                "rawOb": "KJFK 032151Z 23006KT 10SM BKN110 14/03 A3000",
                "obsTime": 1699048260,
                "fltCat": "VFR",
                "wdir": 230,
                "wspd": 6,
                "visib": 10,
            }
        ],
        "https://aviationweather.gov/api/data/metar?ids=KJFK&format=json",
    )

    bundle = AviationWeatherClient().fetch_metar(ids="KJFK")

    assert bundle.source_type == "METAR"
    assert len(bundle.records) == 1
    assert bundle.records[0].location == "KJFK"
    assert "KJFK" in bundle.records[0].summary


@patch("app.services.aviation_weather_client.request_json")
def test_aviation_weather_client_fetches_taf(mock_request) -> None:
    mock_request.return_value = (
        [
            {
                "icaoId": "KJFK",
                "rawTAF": "KJFK 032320Z 0400/0506 VRB05KT P6SM FEW050",
                "issueTime": "2023-11-03 23:20:00.000Z",
            }
        ],
        "https://aviationweather.gov/api/data/taf?ids=KJFK&format=json",
    )

    bundle = AviationWeatherClient().fetch_taf(ids=["KJFK"])

    assert bundle.source_type == "TAF"
    assert len(bundle.records) == 1
    assert "KJFK" in bundle.records[0].summary


@patch("app.services.aviation_weather_client.request_json")
def test_aviation_weather_client_fetches_international_sigmets(mock_request) -> None:
    mock_request.return_value = (
        [
            {
                "icaoId": "PAWU",
                "seriesId": "LIMA 2",
                "hazard": "TURB",
                "firId": "PAZA",
                "firName": "ANCHORAGE",
                "validTimeFrom": 1733364000,
                "validTimeTo": 1733378400,
                "rawSigmet": "WSAK31 PAWU ...",
            }
        ],
        "https://aviationweather.gov/api/data/isigmet?format=json",
    )

    bundle = AviationWeatherClient().fetch_international_sigmets(hazard="turb")

    assert bundle.source_type == "SIGMET"
    assert len(bundle.records) == 1
    assert bundle.records[0].metadata["fir_id"] == "PAZA"
    assert bundle.records[0].record_id == "sigmet-LIMA 2-0"


@patch("app.services.aviation_weather_client.request_json")
def test_aviation_weather_client_assigns_unique_sigmet_record_ids(mock_request) -> None:
    mock_request.return_value = (
        [
            {
                "icaoId": "MMMX",
                "seriesId": "ALFA 1",
                "hazard": "TURB",
                "firId": "MMMX",
                "firName": "MEXICO",
            },
            {
                "icaoId": "MMMX",
                "seriesId": "ALFA 2",
                "hazard": "ICE",
                "firId": "MMMX",
                "firName": "MEXICO",
            },
        ],
        "https://aviationweather.gov/api/data/isigmet?format=json",
    )

    bundle = AviationWeatherClient().fetch_international_sigmets()

    assert [record.record_id for record in bundle.records] == [
        "sigmet-ALFA 1-0",
        "sigmet-ALFA 2-1",
    ]


def test_get_metar_tool_validates_ids() -> None:
    tool = GetMetarTool()
    result = tool.execute({"ids": ""}, ToolContext())

    assert result.success is False
    assert "ids" in (result.error or "").lower()


@patch("app.tools.get_metar.AviationWeatherClient.fetch_metar")
def test_get_metar_tool_success(mock_fetch) -> None:
    mock_fetch.return_value = _sample_metar_bundle()

    tool = GetMetarTool()
    result = tool.execute({"ids": "KJFK"}, ToolContext())

    assert result.success is True
    assert "METAR" in result.summary
    assert "operational_source" in result.data


@patch("app.tools.get_taf.AviationWeatherClient.fetch_taf")
def test_get_taf_tool_success(mock_fetch) -> None:
    mock_fetch.return_value = _sample_taf_bundle()

    tool = GetTafTool()
    result = tool.execute({"ids": "KJFK"}, ToolContext())

    assert result.success is True
    assert "TAF" in result.summary
    assert bundle_to_dict(_sample_taf_bundle())["source_type"] == "TAF"


def test_get_international_sigmets_tool_rejects_invalid_hazard() -> None:
    tool = GetInternationalSigmetsTool()
    result = tool.execute({"hazard": "conv"}, ToolContext())

    assert result.success is False
    assert "hazard" in (result.error or "").lower()
