"""Shared HTTP helpers for operational aviation API clients."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 20.0


class OperationalAPIError(Exception):
    """Raised when an operational API request fails."""


def request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | list[Any], str]:
    """Perform an HTTP request and return parsed JSON plus the request URL."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, params=params, headers=headers)
    except httpx.RequestError as exc:
        logger.warning("Operational API request failed for %s: %s", url, exc)
        raise OperationalAPIError(
            "The operational data provider is temporarily unavailable. Try again shortly."
        ) from exc

    request_url = str(response.request.url)

    if response.status_code == 401:
        raise OperationalAPIError(
            "Authentication failed for the operational data provider. "
            "Verify the server-side API key configuration."
        )
    if response.status_code == 403:
        raise OperationalAPIError(
            "Access to the operational data provider is not available for this account."
        )
    if response.status_code == 404:
        raise OperationalAPIError(
            "No operational data was found for the requested parameters."
        )
    if response.status_code == 429:
        raise OperationalAPIError(
            "The operational data provider rate limit was exceeded. Try again later."
        )
    if response.status_code >= 500:
        raise OperationalAPIError(
            "The operational data provider returned a temporary server error."
        )
    if response.status_code >= 400:
        raise OperationalAPIError(
            f"The operational data provider rejected the request (status {response.status_code})."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise OperationalAPIError(
            "The operational data provider returned an invalid response."
        ) from exc

    return payload, request_url
