"""
Full-stack ingestion pipeline: API -> MongoDB Staging -> SQL Warehouse.

This module orchestrates the Tennis Rankings Explorer's three-layer architecture:
1. API Extraction: Fetch raw JSON from SportRadar Tennis API (3 endpoints)
2. MongoDB Staging: Upsert raw documents into staging layer (tennis_staging database)
3. ETL Transform & Load: Extract, flatten, and load normalized data into SQL warehouse

The pipeline provides robust error handling, transaction management, and detailed logging.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from tennis_etl.api import SportRadarApiError, SportRadarTennisClient
from tennis_etl.config import Settings
from tennis_etl.database import build_engine, create_schema, session_factory
from tennis_etl.loader import load_all
from tennis_etl.transforms import (
    transform_competitions,
    transform_complexes,
    transform_doubles_rankings,
)

LOGGER = logging.getLogger(__name__)


# ===========================
# MongoDB Staging Configuration
# ===========================

MONGODB_DATABASE_NAME = "tennis_staging"
MONGODB_COLLECTIONS = {
    "competitions": "raw_competitions",
    "complexes": "raw_complexes",
    "rankings": "raw_rankings",
}


@dataclass(frozen=True)
class StagingCounts:
    """Document counts written to MongoDB staging collections."""

    competitions: int = 0
    complexes: int = 0
    rankings: int = 0

    def __str__(self) -> str:
        return (
            f"Staging staged: competitions={self.competitions}, "
            f"complexes={self.complexes}, rankings={self.rankings}"
        )


@dataclass(frozen=True)
class PipelineCounts:
    """Aggregate counts for entire ingestion pipeline."""

    staging: StagingCounts = StagingCounts()
    warehouse_categories: int = 0
    warehouse_competitions: int = 0
    warehouse_complexes: int = 0
    warehouse_venues: int = 0
    warehouse_competitors: int = 0
    warehouse_rankings: int = 0

    def __str__(self) -> str:
        warehouse_total = (
            self.warehouse_categories
            + self.warehouse_competitions
            + self.warehouse_complexes
            + self.warehouse_venues
            + self.warehouse_competitors
            + self.warehouse_rankings
        )
        return (
            f"Pipeline complete: {self.staging}; "
            f"warehouse_total={warehouse_total} "
            f"(categories={self.warehouse_categories}, "
            f"competitions={self.warehouse_competitions}, "
            f"complexes={self.warehouse_complexes}, "
            f"venues={self.warehouse_venues}, "
            f"competitors={self.warehouse_competitors}, "
            f"rankings={self.warehouse_rankings})"
        )


# ===========================
# MongoDB Staging Operations
# ===========================


class MongoStagingError(RuntimeError):
    """Raised when MongoDB staging operations fail."""


def _create_mongo_client(mongo_url: str, timeout_ms: int = 5000) -> MongoClient:
    """
    Create a MongoDB client with connection validation.

    Args:
        mongo_url: Connection string (e.g., 'mongodb://localhost:27017')
        timeout_ms: Server selection timeout in milliseconds

    Returns:
        Authenticated MongoClient instance

    Raises:
        MongoStagingError: If connection fails
    """
    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=timeout_ms)
        client.admin.command("ping")
        LOGGER.info("MongoDB connection established: %s", mongo_url)
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        raise MongoStagingError(
            f"Failed to connect to MongoDB at {mongo_url}: {exc}"
        ) from exc


def _upsert_mongo_collection(
    db_name: str,
    collection_name: str,
    documents: list[dict[str, Any]],
    client: MongoClient,
) -> int:
    """
    Upsert documents into a MongoDB collection using replace_one with upsert=True.

    Each document must have an '_id' field for idempotent upserts.
    If '_id' is not present, MongoDB will auto-generate it (non-idempotent).

    Args:
        db_name: Database name
        collection_name: Collection name
        documents: List of documents to upsert
        client: MongoClient instance

    Returns:
        Number of documents upserted

    Raises:
        MongoStagingError: If upsert fails
    """
    if not documents:
        return 0

    try:
        db = client[db_name]
        collection = db[collection_name]

        upserted_count = 0
        for doc in documents:
            if "_id" not in doc:
                LOGGER.warning(
                    "Document in %s.%s missing _id field; MongoDB will auto-generate",
                    db_name,
                    collection_name,
                )
            try:
                result = collection.replace_one(
                    {"_id": doc.get("_id", doc)},
                    doc,
                    upsert=True,
                )
                upserted_count += 1
            except Exception as exc:
                LOGGER.error(
                    "Failed to upsert document to %s.%s: %s",
                    db_name,
                    collection_name,
                    exc,
                )
                raise

        LOGGER.info(
            "Upserted %d documents to %s.%s",
            upserted_count,
            db_name,
            collection_name,
        )
        return upserted_count

    except Exception as exc:
        raise MongoStagingError(
            f"MongoDB staging failed for {db_name}.{collection_name}: {exc}"
        ) from exc


def stage_to_mongodb(
    competitions_payload: dict[str, Any],
    complexes_payload: dict[str, Any],
    rankings_payload: dict[str, Any],
    mongo_url: str,
) -> StagingCounts:
    """
    Stage raw API payloads into MongoDB collections for durability and audit.

    Each payload is stored as a single document with a fixed _id to enable
    idempotent reruns. MongoDB will overwrite the previous version on retry.

    Args:
        competitions_payload: Raw competitions API response
        complexes_payload: Raw complexes API response
        rankings_payload: Raw rankings API response
        mongo_url: MongoDB connection string

    Returns:
        StagingCounts with document counts

    Raises:
        MongoStagingError: If staging fails
    """
    client: MongoClient | None = None
    try:
        client = _create_mongo_client(mongo_url)

        # Each endpoint response is stored as a single snapshot document
        # Using fixed IDs allows reruns to overwrite without accumulating duplicates
        competition_docs = [
            {
                "_id": "current_snapshot",
                "endpoint": "competitions",
                "payload": competitions_payload,
            }
        ]
        complexes_docs = [
            {
                "_id": "current_snapshot",
                "endpoint": "complexes",
                "payload": complexes_payload,
            }
        ]
        rankings_docs = [
            {
                "_id": "current_snapshot",
                "endpoint": "rankings",
                "payload": rankings_payload,
            }
        ]

        competitions_count = _upsert_mongo_collection(
            MONGODB_DATABASE_NAME,
            MONGODB_COLLECTIONS["competitions"],
            competition_docs,
            client,
        )
        complexes_count = _upsert_mongo_collection(
            MONGODB_DATABASE_NAME,
            MONGODB_COLLECTIONS["complexes"],
            complexes_docs,
            client,
        )
        rankings_count = _upsert_mongo_collection(
            MONGODB_DATABASE_NAME,
            MONGODB_COLLECTIONS["rankings"],
            rankings_docs,
            client,
        )

        return StagingCounts(
            competitions=competitions_count,
            complexes=complexes_count,
            rankings=rankings_count,
        )

    except MongoStagingError:
        raise
    except Exception as exc:
        raise MongoStagingError(f"Unexpected error staging to MongoDB: {exc}") from exc
    finally:
        if client:
            client.close()
            LOGGER.info("MongoDB connection closed")


def extract_from_mongodb(mongo_url: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Extract raw payloads from MongoDB staging collections.

    Returns the current_snapshot documents from each collection. If collection
    is empty, returns empty dict {}. This allows the ETL to handle gracefully.

    Args:
        mongo_url: MongoDB connection string

    Returns:
        Tuple of (competitions_payload, complexes_payload, rankings_payload)

    Raises:
        MongoStagingError: If extraction fails
    """
    client: MongoClient | None = None
    try:
        client = _create_mongo_client(mongo_url)

        db = client[MONGODB_DATABASE_NAME]

        # Extract current_snapshot from each collection
        competitions_doc = db[MONGODB_COLLECTIONS["competitions"]].find_one(
            {"_id": "current_snapshot"}
        )
        complexes_doc = db[MONGODB_COLLECTIONS["complexes"]].find_one(
            {"_id": "current_snapshot"}
        )
        rankings_doc = db[MONGODB_COLLECTIONS["rankings"]].find_one(
            {"_id": "current_snapshot"}
        )

        # Extract payload or return empty dict if document not found
        competitions_payload = (
            competitions_doc.get("payload", {})
            if competitions_doc
            else {}
        )
        complexes_payload = (
            complexes_doc.get("payload", {})
            if complexes_doc
            else {}
        )
        rankings_payload = (
            rankings_doc.get("payload", {})
            if rankings_doc
            else {}
        )

        LOGGER.info(
            "Extracted payloads from MongoDB staging: "
            "competitions=%s, complexes=%s, rankings=%s",
            "present" if competitions_payload else "empty",
            "present" if complexes_payload else "empty",
            "present" if rankings_payload else "empty",
        )

        return competitions_payload, complexes_payload, rankings_payload

    except MongoStagingError:
        raise
    except Exception as exc:
        raise MongoStagingError(
            f"Failed to extract from MongoDB staging: {exc}"
        ) from exc
    finally:
        if client:
            client.close()


# ===========================
# Full Pipeline Orchestration
# ===========================


def run_full_pipeline(
    settings: Settings,
    mongo_url: str = "mongodb://localhost:27017",
    skip_staging: bool = False,
) -> PipelineCounts:
    """
    Execute full three-layer ingestion pipeline.

    1. Fetch raw JSON from SportRadar Tennis API (3 endpoints)
    2. Stage raw responses into MongoDB (optional, can skip)
    3. Extract from MongoDB (or directly from API if skip_staging)
    4. Transform and flatten nested structures
    5. Load into SQL warehouse with upserts

    Args:
        settings: Configured Settings from environment or explicit config
        mongo_url: MongoDB connection string (default localhost:27017)
        skip_staging: If True, skip MongoDB and go direct API->SQL (for testing)

    Returns:
        PipelineCounts with all write counts

    Raises:
        SportRadarApiError: If API fetch fails
        MongoStagingError: If MongoDB staging fails
        SQLAlchemyError: If SQL load fails
    """
    LOGGER.info("=" * 60)
    LOGGER.info("Starting Tennis Rankings Explorer ingestion pipeline")
    LOGGER.info("=" * 60)

    # Step 1: API Extraction
    LOGGER.info("[PHASE 1A] Fetching raw data from SportRadar Tennis API...")
    client = SportRadarTennisClient(
        api_key=settings.sportradar_api_key,
        access_level=settings.access_level,
        language_code=settings.language_code,
        timeout_seconds=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
    )

    try:
        competitions_payload = client.get_competitions()
        complexes_payload = client.get_complexes()
        rankings_payload = client.get_doubles_competitor_rankings()
        LOGGER.info("[PHASE 1A] API extraction complete")
    except SportRadarApiError:
        LOGGER.exception("[PHASE 1A] API extraction failed")
        raise

    staging_counts = StagingCounts()

    # Step 2: MongoDB Staging (optional)
    if not skip_staging:
        LOGGER.info("[PHASE 1B] Staging raw payloads to MongoDB...")
        try:
            staging_counts = stage_to_mongodb(
                competitions_payload,
                complexes_payload,
                rankings_payload,
                mongo_url,
            )
            LOGGER.info("[PHASE 1B] MongoDB staging complete: %s", staging_counts)
        except MongoStagingError:
            LOGGER.exception("[PHASE 1B] MongoDB staging failed")
            raise
    else:
        LOGGER.info("[PHASE 1B] Skipping MongoDB staging (skip_staging=True)")

    # Step 3: Extract from MongoDB (or use API payloads directly)
    if not skip_staging:
        LOGGER.info("[PHASE 1C] Extracting from MongoDB staging...")
        try:
            (
                competitions_payload,
                complexes_payload,
                rankings_payload,
            ) = extract_from_mongodb(mongo_url)
            LOGGER.info("[PHASE 1C] MongoDB extraction complete")
        except MongoStagingError:
            LOGGER.exception("[PHASE 1C] MongoDB extraction failed")
            raise
    else:
        LOGGER.info("[PHASE 1C] Using API payloads directly (skip_staging=True)")

    # Step 4: Transform
    LOGGER.info("[PHASE 1C] Transforming and flattening nested structures...")
    try:
        categories, competitions = transform_competitions(competitions_payload)
        complexes, venues = transform_complexes(complexes_payload)
        competitors, rankings = transform_doubles_rankings(rankings_payload)
        LOGGER.info(
            "[PHASE 1C] Transform complete: "
            "categories=%d, competitions=%d, complexes=%d, venues=%d, "
            "competitors=%d, rankings=%d",
            len(categories),
            len(competitions),
            len(complexes),
            len(venues),
            len(competitors),
            len(rankings),
        )
    except Exception:
        LOGGER.exception("[PHASE 1C] Transform failed")
        raise

    # Step 5: SQL Schema and Load
    LOGGER.info("[PHASE 1C] Initializing SQL warehouse schema...")
    engine = build_engine(settings.database_url)
    create_schema(engine)
    LOGGER.info("[PHASE 1C] SQL schema ready")

    LOGGER.info("[PHASE 1C] Loading transformed rows into SQL warehouse...")
    sessions = session_factory(engine)
    try:
        with sessions() as session:
            load_counts = load_all(
                session=session,
                categories=categories,
                competitions=competitions,
                complexes=complexes,
                venues=venues,
                competitors=competitors,
                rankings=rankings,
            )
        LOGGER.info("[PHASE 1C] SQL load complete: %s", load_counts)
    except Exception:
        LOGGER.exception("[PHASE 1C] SQL load failed")
        raise

    # Final Summary
    pipeline_counts = PipelineCounts(
        staging=staging_counts,
        warehouse_categories=load_counts.categories,
        warehouse_competitions=load_counts.competitions,
        warehouse_complexes=load_counts.complexes,
        warehouse_venues=load_counts.venues,
        warehouse_competitors=load_counts.competitors,
        warehouse_rankings=load_counts.rankings,
    )

    LOGGER.info("=" * 60)
    LOGGER.info("Pipeline success: %s", pipeline_counts)
    LOGGER.info("=" * 60)

    return pipeline_counts


def main() -> None:
    """CLI entrypoint for the full ingestion pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    # Load settings from environment
    settings = Settings.from_environment()

    # Read MongoDB URL from environment or use default
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    # Allow CLI override to skip staging for quick iteration
    skip_staging = os.getenv("SKIP_STAGING", "false").lower() == "true"

    try:
        run_full_pipeline(settings, mongo_url, skip_staging)
    except (SportRadarApiError, MongoStagingError, Exception):
        LOGGER.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    main()
