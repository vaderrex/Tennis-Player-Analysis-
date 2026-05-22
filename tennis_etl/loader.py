"""Database load operations for transformed Phase 1 rows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from tennis_etl.database import upsert_rows
from tennis_etl.models import (
    Category,
    Competition,
    Competitor,
    CompetitorRanking,
    Complex,
    Venue,
)


@dataclass(frozen=True)
class LoadCounts:
    """Counts written by one ETL load."""

    categories: int = 0
    competitions: int = 0
    complexes: int = 0
    venues: int = 0
    competitors: int = 0
    rankings: int = 0


def load_all(
    session: Session,
    categories: list[dict],
    competitions: list[dict],
    complexes: list[dict],
    venues: list[dict],
    competitors: list[dict],
    rankings: list[dict],
) -> LoadCounts:
    """Load transformed rows in foreign-key dependency order."""
    try:
        counts = LoadCounts(
            categories=upsert_rows(
                session,
                Category.__table__,
                categories,
                ["category_id"],
                ["category_name"],
            ),
            competitions=upsert_rows(
                session,
                Competition.__table__,
                competitions,
                ["competition_id"],
                [
                    "competition_name",
                    "parent_id",
                    "type",
                    "gender",
                    "category_id",
                ],
            ),
            complexes=upsert_rows(
                session,
                Complex.__table__,
                complexes,
                ["complex_id"],
                ["complex_name"],
            ),
            venues=upsert_rows(
                session,
                Venue.__table__,
                venues,
                ["venue_id"],
                [
                    "venue_name",
                    "city_name",
                    "country_name",
                    "country_code",
                    "timezone",
                    "complex_id",
                ],
            ),
            competitors=upsert_rows(
                session,
                Competitor.__table__,
                competitors,
                ["competitor_id"],
                ["name", "country", "country_code", "abbreviation"],
            ),
            rankings=upsert_rows(
                session,
                CompetitorRanking.__table__,
                rankings,
                ["competitor_id"],
                [
                    "rank",
                    "movement",
                    "points",
                    "competitions_played",
                ],
            ),
        )
        session.commit()
        return counts
    except (IntegrityError, SQLAlchemyError):
        session.rollback()
        raise
