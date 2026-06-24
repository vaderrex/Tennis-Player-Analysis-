"""Reusable Python API request helpers for three endpoint patterns."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode, urljoin

import requests

# Optional MongoDB storage
try:
    from tennis_etl.mongo_storage import (
        store_competitions,
        store_complexes,
        store_rankings,
        retrieve_api_response,
    )
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 5
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.example.com/v1")
API_TOKEN = os.getenv("API_TOKEN", "")


class ApiRequestError(RuntimeError):
    """Raised when an API request fails with a handled HTTP status."""

    def __init__(self, status_code: int, message: str, response_body: Any) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def build_headers(extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    """Build JSON and bearer-token headers with optional overrides."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('API_TOKEN', API_TOKEN)}",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def build_url(path: str, query_params: dict[str, Any] | None = None) -> str:
    """Build a complete URL with optional query parameters."""
    base_url = os.getenv("API_BASE_URL", API_BASE_URL).rstrip("/") + "/"
    normalized_path = path.lstrip("/")
    url = urljoin(base_url, normalized_path)

    if not query_params:
        return url

    filtered_params = {
        key: value
        for key, value in query_params.items()
        if value is not None and value != ""
    }
    if not filtered_params:
        return url

    return f"{url}?{urlencode(filtered_params)}"


def request_json(
    method: str,
    path: str,
    *,
    query_params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """Execute a JSON API request with timeout and handled HTTP errors."""
    if not os.getenv("API_TOKEN", API_TOKEN):
        raise ValueError("Missing API_TOKEN environment variable.")

    try:
        response = requests.request(
            method=method,
            url=build_url(path, query_params),
            headers=build_headers(headers),
            json=body,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise TimeoutError(
            f"Request timed out after {DEFAULT_TIMEOUT_SECONDS * 1000}ms."
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Request failed before receiving a response: {exc}") from exc

    response_body = parse_response_body(response)
    if response.status_code >= 400:
        raise build_http_error(response.status_code, response_body)
    return response_body


def parse_response_body(response: requests.Response) -> Any:
    """Parse JSON responses and gracefully handle plain-text bodies."""
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    return {"message": response.text} if response.text else {}


def build_http_error(status_code: int, response_body: Any) -> ApiRequestError:
    """Build a clear exception for common API failure statuses."""
    detail = "No error body."
    if isinstance(response_body, dict):
        detail = response_body.get("message") or response_body.get("error") or detail

    status_messages = {
        400: "Bad request. Check query parameters or JSON payload.",
        401: "Unauthorized. Check API token or auth headers.",
        500: "Server error. Retry later or contact the API owner.",
    }
    message = status_messages.get(status_code, f"HTTP {status_code} request failed.")
    return ApiRequestError(status_code, f"{message} Detail: {detail}", response_body)


def fetch_data(search: str | None = None, limit: int = 25, page: int = 1) -> Any:
    """GET: Fetch data with query parameters."""
    return request_json(
        "GET",
        "/items",
        query_params={"search": search, "limit": limit, "page": page},
    )


def submit_payload(payload: dict[str, Any]) -> Any:
    """POST: Submit a JSON payload."""
    return request_json("POST", "/items", body=payload)


def update_resource(resource_id: str, patch_payload: dict[str, Any]) -> Any:
    """PATCH: Update an existing resource."""
    if not resource_id:
        raise ValueError("resource_id is required.")
    return request_json("PATCH", f"/items/{resource_id}", body=patch_payload)


# ===========================
# MongoDB Storage Integration
# ===========================


def store_api_response_to_mongodb(
    response_data: dict[str, Any],
    collection_type: str,
    mongo_url: str | None = None,
) -> dict[str, Any]:
    """
    Store API response in MongoDB and return the response.

    Args:
        response_data: API response JSON
        collection_type: One of 'competitions', 'complexes', 'rankings'
        mongo_url: MongoDB connection URL (defaults to DATABASE_URL env var)

    Returns:
        The response_data passed in (for chaining)
    """
    if not MONGO_AVAILABLE:
        LOGGER.warning("MongoDB storage not available; skipping storage.")
        return response_data

    if not mongo_url:
        mongo_url = os.getenv("DATABASE_URL")
        if not mongo_url:
            LOGGER.warning(
                "DATABASE_URL not set; cannot store API response in MongoDB."
            )
            return response_data

    try:
        if collection_type == "competitions":
            store_competitions(mongo_url, response_data)
        elif collection_type == "complexes":
            store_complexes(mongo_url, response_data)
        elif collection_type == "rankings":
            store_rankings(mongo_url, response_data)
        else:
            LOGGER.warning(
                "Unknown collection_type '%s'; skipping MongoDB storage.",
                collection_type,
            )
        LOGGER.info("API response stored in MongoDB: %s", collection_type)
    except Exception as exc:
        LOGGER.error("Failed to store API response in MongoDB: %s", exc)

    return response_data


def retrieve_api_response_from_mongodb(
    collection_type: str,
    mongo_url: str | None = None,
) -> dict[str, Any] | None:
    """
    Retrieve stored API response from MongoDB.

    Args:
        collection_type: One of 'competitions', 'complexes', 'rankings'
        mongo_url: MongoDB connection URL (defaults to DATABASE_URL env var)

    Returns:
        Stored API response data or None if not found
    """
    if not MONGO_AVAILABLE:
        LOGGER.warning("MongoDB storage not available; cannot retrieve.")
        return None

    if not mongo_url:
        mongo_url = os.getenv("DATABASE_URL")
        if not mongo_url:
            LOGGER.warning("DATABASE_URL not set; cannot retrieve from MongoDB.")
            return None

    try:
        from tennis_etl.mongo_storage import MONGODB_COLLECTIONS

        collection_name = MONGODB_COLLECTIONS.get(collection_type)
        if not collection_name:
            LOGGER.warning(
                "Unknown collection_type '%s'; cannot retrieve.",
                collection_type,
            )
            return None

        data = retrieve_api_response(
            mongo_url, collection_name, endpoint_id=collection_type
        )
        if data:
            LOGGER.info("Retrieved API response from MongoDB: %s", collection_type)
        return data
    except Exception as exc:
        LOGGER.error("Failed to retrieve API response from MongoDB: %s", exc)
        return None


if __name__ == "__main__":
    print("Import this module and call fetch_data, submit_payload, or update_resource.")
    print("For MongoDB storage, call store_api_response_to_mongodb or retrieve_api_response_from_mongodb.")
