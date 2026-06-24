"""Runnable Phase 1 ETL for Tennis Rankings Explorer."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from tennis_etl.api import SportRadarApiError, SportRadarTennisClient
from tennis_etl.config import Settings
from tennis_etl.csv_exporter import CSVExporter
from tennis_etl.database import build_engine, create_schema, session_factory
from tennis_etl.loader import load_all
from tennis_etl.transforms import (
    transform_competitions,
    transform_complexes,
    transform_doubles_rankings,
)

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Fetch Phase 1 feeds, flatten them, and upsert them into SQL.
    
    Optional CLI arguments:
        --export-csv: Export transformed data to CSV files
        --csv-output: Directory for CSV files (default: etl_output)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Tennis Rankings ETL Pipeline"
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export transformed data to CSV files",
    )
    parser.add_argument(
        "--csv-output",
        type=str,
        default="etl_output",
        help="Directory for CSV exports (default: etl_output)",
    )
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    settings = Settings.from_environment()
    client = SportRadarTennisClient(
        api_key=settings.sportradar_api_key,
        access_level=settings.access_level,
        language_code=settings.language_code,
        timeout_seconds=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
    )
    engine = build_engine(settings.database_url)
    create_schema(engine)

    try:
        categories, competitions = transform_competitions(
            client.get_competitions()
        )
        complexes, venues = transform_complexes(client.get_complexes())
        competitors, rankings = transform_doubles_rankings(
            client.get_doubles_competitor_rankings()
        )
    except SportRadarApiError:
        LOGGER.exception("Phase 1 SportRadar extraction failed.")
        raise

    # Export to CSV if requested
    if args.export_csv:
        try:
            exporter = CSVExporter(output_dir=args.csv_output)
            exporter.export_all(
                categories=categories,
                competitions=competitions,
                complexes=complexes,
                venues=venues,
                competitors=competitors,
                rankings=rankings,
            )
        except Exception as e:
            LOGGER.warning(f"CSV export failed (pipeline will continue): {e}")

    sessions = session_factory(engine)
    with sessions() as session:
        counts = load_all(
            session=session,
            categories=categories,
            competitions=competitions,
            complexes=complexes,
            venues=venues,
            competitors=competitors,
            rankings=rankings,
        )

    LOGGER.info("Phase 1 load complete: %s", counts)


if __name__ == "__main__":
    main()
