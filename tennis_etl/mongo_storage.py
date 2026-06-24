"""MongoDB storage for raw API responses."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

LOGGER = logging.getLogger(__name__)

MONGODB_DATABASE_NAME = "tennis_staging"
MONGODB_COLLECTIONS = {
    "competitions": "raw_competitions",
    "complexes": "raw_complexes",
    "rankings": "raw_rankings",
}


class MongoStorageError(RuntimeError):
    """Raised when MongoDB storage operations fail."""


def create_mongo_client(mongo_url: str, timeout_ms: int = 5000) -> MongoClient:
    """
    Create a MongoDB client with connection validation.

    Args:
        mongo_url: Connection string (e.g., 'mongodb://localhost:27017')
        timeout_ms: Server selection timeout in milliseconds

    Returns:
        Authenticated MongoClient instance

    Raises:
        MongoStorageError: If connection fails
    """
    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=timeout_ms)
        client.admin.command("ping")
        LOGGER.info("MongoDB connection established: %s", mongo_url)
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        raise MongoStorageError(
            f"Failed to connect to MongoDB at {mongo_url}: {exc}"
        ) from exc


def store_api_response(
    mongo_url: str,
    collection_name: str,
    response_data: dict[str, Any],
    endpoint_id: str | None = None,
) -> str:
    """
    Store raw API response in MongoDB with metadata.

    Args:
        mongo_url: MongoDB connection string
        collection_name: Target collection (e.g., 'raw_competitions', 'raw_complexes', 'raw_rankings')
        response_data: Raw API JSON response
        endpoint_id: Optional identifier for the endpoint/request

    Returns:
        MongoDB document ID (string representation)

    Raises:
        MongoStorageError: If storage fails
    """
    if collection_name not in MONGODB_COLLECTIONS.values():
        raise ValueError(
            f"Invalid collection_name '{collection_name}'. "
            f"Must be one of: {list(MONGODB_COLLECTIONS.values())}"
        )

    try:
        client = create_mongo_client(mongo_url)
        db = client[MONGODB_DATABASE_NAME]
        collection = db[collection_name]

        # Prepare document with metadata
        document = {
            "data": response_data,
            "endpoint_id": endpoint_id or "unknown",
            "stored_at": datetime.utcnow(),
            "source": "api",
        }

        # Upsert by endpoint_id for idempotency
        result = collection.replace_one(
            {"endpoint_id": endpoint_id or "unknown"},
            document,
            upsert=True,
        )

        doc_id = str(result.upserted_id or result.matched_count)
        LOGGER.info(
            "Stored API response in %s.%s with endpoint_id=%s",
            MONGODB_DATABASE_NAME,
            collection_name,
            endpoint_id,
        )
        return doc_id

    except Exception as exc:
        raise MongoStorageError(
            f"Failed to store API response in {collection_name}: {exc}"
        ) from exc
    finally:
        if "client" in locals():
            client.close()


def store_competitions(
    mongo_url: str, competitions_payload: dict[str, Any]
) -> str:
    """Store competitions API response."""
    return store_api_response(
        mongo_url,
        MONGODB_COLLECTIONS["competitions"],
        competitions_payload,
        endpoint_id="competitions",
    )


def store_complexes(mongo_url: str, complexes_payload: dict[str, Any]) -> str:
    """Store complexes API response."""
    return store_api_response(
        mongo_url,
        MONGODB_COLLECTIONS["complexes"],
        complexes_payload,
        endpoint_id="complexes",
    )


def store_rankings(mongo_url: str, rankings_payload: dict[str, Any]) -> str:
    """Store rankings API response."""
    return store_api_response(
        mongo_url,
        MONGODB_COLLECTIONS["rankings"],
        rankings_payload,
        endpoint_id="rankings",
    )


def retrieve_api_response(
    mongo_url: str, collection_name: str, endpoint_id: str | None = None
) -> dict[str, Any] | None:
    """
    Retrieve stored API response from MongoDB.

    Args:
        mongo_url: MongoDB connection string
        collection_name: Source collection
        endpoint_id: Optional identifier for the endpoint/request

    Returns:
        Retrieved API response data or None if not found

    Raises:
        MongoStorageError: If retrieval fails
    """
    try:
        client = create_mongo_client(mongo_url)
        db = client[MONGODB_DATABASE_NAME]
        collection = db[collection_name]

        query = (
            {"endpoint_id": endpoint_id} if endpoint_id else {}
        )
        document = collection.find_one(query, sort=[("stored_at", -1)])

        if document:
            LOGGER.info(
                "Retrieved API response from %s.%s",
                MONGODB_DATABASE_NAME,
                collection_name,
            )
            return document.get("data")

        LOGGER.warning(
            "No API response found in %s.%s",
            MONGODB_DATABASE_NAME,
            collection_name,
        )
        return None

    except Exception as exc:
        raise MongoStorageError(
            f"Failed to retrieve API response from {collection_name}: {exc}"
        ) from exc
    finally:
        if "client" in locals():
            client.close()
