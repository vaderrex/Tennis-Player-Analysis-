"""Create Phase 1 database tables without calling SportRadar."""

from __future__ import annotations

import logging
import os

from tennis_etl.database import build_engine, create_schema

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Create the six SQLAlchemy-managed tables."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Missing required environment variable: DATABASE_URL")

    create_schema(build_engine(database_url))
    LOGGER.info("Phase 1 schema created or already present.")


if __name__ == "__main__":
    main()
