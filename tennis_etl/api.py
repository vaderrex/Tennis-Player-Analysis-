"""Requests-based SportRadar Tennis v3 API client."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException

LOGGER = logging.getLogger(__name__)


class SportRadarApiError(RuntimeError):
    """Raised when the SportRadar API cannot return usable data."""


class SportRadarRateLimitError(SportRadarApiError):
    """Raised when retries cannot clear an HTTP 429 response."""


class SportRadarTennisClient:
    """Small API client for Phase 1 Tennis v3 endpoints."""

    base_url = "https://api.sportradar.com/tennis"

    def __init__(
        self,
        api_key: str,
        access_level: str = "trial",
        language_code: str = "en",
        timeout_seconds: int = 20,
        max_retries: int = 4,
    ) -> None:
        self.api_key = api_key
        self.access_level = access_level
        self.language_code = language_code
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})

    def get_competitions(self) -> dict[str, Any]:
        """Fetch all available tennis competitions."""
        return self._get_json("competitions.json")

    def get_complexes(self) -> dict[str, Any]:
        """Fetch complexes and their nested venues."""
        return self._get_json("complexes.json")

    def get_doubles_competitor_rankings(self) -> dict[str, Any]:
        """Fetch ATP and WTA doubles competitor ranking lists."""
        return self._get_json("double_competitors_rankings.json")

    def _get_json(self, endpoint: str) -> dict[str, Any]:
        url = (
            f"{self.base_url}/{self.access_level}/v3/"
            f"{self.language_code}/{endpoint}"
        )
        response: Response | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                if response.status_code == 429:
                    wait_seconds = _retry_after_seconds(response, attempt)
                    LOGGER.warning(
                        "SportRadar rate limit reached for %s. Retrying in %ss.",
                        endpoint,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                if 500 <= response.status_code < 600 and attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue

                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise SportRadarApiError(
                        f"Unexpected JSON payload for {endpoint}: root is not an object."
                    )
                return payload
            except ValueError as exc:
                raise SportRadarApiError(
                    f"SportRadar returned invalid JSON for {endpoint}."
                ) from exc
            except RequestException as exc:
                if attempt < self.max_retries:
                    LOGGER.warning(
                        "SportRadar request failed for %s on attempt %s: %s",
                        endpoint,
                        attempt + 1,
                        exc,
                    )
                    time.sleep(2**attempt)
                    continue
                raise SportRadarApiError(
                    f"SportRadar request failed for {endpoint}: {exc}"
                ) from exc

        status_code = response.status_code if response is not None else "unknown"
        raise SportRadarRateLimitError(
            f"SportRadar rate limit persisted for {endpoint}; last status {status_code}."
        )


def _retry_after_seconds(response: Response, attempt: int) -> int:
    """Read Retry-After when available, otherwise use exponential backoff."""
    retry_after = response.headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return max(1, int(retry_after))
    return min(60, 2**attempt)
