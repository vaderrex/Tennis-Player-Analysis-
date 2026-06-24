"""Analytical query wrappers for Streamlit-facing DataFrames."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection

Connectable = str | Engine | Connection | None
SqlParams = Mapping[str, Any] | None


def competitions_with_categories(connectable: Connectable = None) -> pd.DataFrame:
    """List competitions with their category names."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            comp.competition_id,
            comp.competition_name,
            comp.type,
            comp.gender,
            cat.category_id,
            cat.category_name
        FROM competitions AS comp
        JOIN categories AS cat
            ON cat.category_id = comp.category_id
        ORDER BY cat.category_name, comp.competition_name
        """,
    )


def competition_counts_by_category(connectable: Connectable = None) -> pd.DataFrame:
    """Count competitions in each category."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            cat.category_id,
            cat.category_name,
            COUNT(comp.competition_id) AS competition_count
        FROM categories AS cat
        LEFT JOIN competitions AS comp
            ON comp.category_id = cat.category_id
        GROUP BY cat.category_id, cat.category_name
        ORDER BY competition_count DESC, cat.category_name
        """,
    )


def doubles_competitions(connectable: Connectable = None) -> pd.DataFrame:
    """List competitions whose SportRadar type is doubles."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            comp.competition_id,
            comp.competition_name,
            comp.gender,
            cat.category_name
        FROM competitions AS comp
        JOIN categories AS cat
            ON cat.category_id = comp.category_id
        WHERE LOWER(comp.type) = :competition_type
        ORDER BY cat.category_name, comp.competition_name
        """,
        {"competition_type": "doubles"},
    )


def competitions_by_category(
    category_name: str,
    connectable: Connectable = None,
) -> pd.DataFrame:
    """List competitions for a category name such as 'ITF Men'."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            comp.competition_id,
            comp.competition_name,
            comp.type,
            comp.gender,
            cat.category_name
        FROM competitions AS comp
        JOIN categories AS cat
            ON cat.category_id = comp.category_id
        WHERE cat.category_name = :category_name
        ORDER BY comp.competition_name
        """,
        {"category_name": category_name},
    )


def competition_parent_child_relationships(
    connectable: Connectable = None,
) -> pd.DataFrame:
    """List competitions with their optional parent competition."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            child.competition_id AS child_competition_id,
            child.competition_name AS child_competition_name,
            parent.competition_id AS parent_competition_id,
            parent.competition_name AS parent_competition_name,
            cat.category_name
        FROM competitions AS child
        LEFT JOIN competitions AS parent
            ON parent.competition_id = child.parent_id
        JOIN categories AS cat
            ON cat.category_id = child.category_id
        WHERE child.parent_id IS NOT NULL
        ORDER BY parent.competition_name, child.competition_name
        """,
    )


def competition_type_distribution(connectable: Connectable = None) -> pd.DataFrame:
    """Count competitions by SportRadar competition type."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            COALESCE(comp.type, 'Unknown') AS competition_type,
            COUNT(*) AS competition_count
        FROM competitions AS comp
        GROUP BY COALESCE(comp.type, 'Unknown')
        ORDER BY competition_count DESC, competition_type
        """,
    )


def top_level_competitions(connectable: Connectable = None) -> pd.DataFrame:
    """List competitions that do not have a parent competition."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            comp.competition_id,
            comp.competition_name,
            comp.type,
            comp.gender,
            cat.category_name
        FROM competitions AS comp
        JOIN categories AS cat
            ON cat.category_id = comp.category_id
        WHERE comp.parent_id IS NULL
        ORDER BY cat.category_name, comp.competition_name
        """,
    )


def venues_with_complexes(connectable: Connectable = None) -> pd.DataFrame:
    """List venues with their complex names."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            venue.venue_id,
            venue.venue_name,
            venue.city_name,
            venue.country_name,
            venue.country_code,
            venue.timezone,
            complex.complex_id,
            complex.complex_name
        FROM venues AS venue
        JOIN complexes AS complex
            ON complex.complex_id = venue.complex_id
        ORDER BY complex.complex_name, venue.venue_name
        """,
    )


def venue_counts_by_complex(connectable: Connectable = None) -> pd.DataFrame:
    """Count venues in every complex."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            complex.complex_id,
            complex.complex_name,
            COUNT(venue.venue_id) AS venue_count
        FROM complexes AS complex
        LEFT JOIN venues AS venue
            ON venue.complex_id = complex.complex_id
        GROUP BY complex.complex_id, complex.complex_name
        ORDER BY venue_count DESC, complex.complex_name
        """,
    )


def venues_by_country(
    country_name: str,
    connectable: Connectable = None,
) -> pd.DataFrame:
    """List venues in a specific country."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            venue.venue_id,
            venue.venue_name,
            venue.city_name,
            venue.country_name,
            venue.country_code,
            venue.timezone,
            complex.complex_name
        FROM venues AS venue
        JOIN complexes AS complex
            ON complex.complex_id = venue.complex_id
        WHERE venue.country_name = :country_name
        ORDER BY venue.city_name, venue.venue_name
        """,
        {"country_name": country_name},
    )


def venue_timezones(connectable: Connectable = None) -> pd.DataFrame:
    """List distinct venue timezones and their venue counts."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            COALESCE(venue.timezone, 'Unknown') AS timezone,
            COUNT(*) AS venue_count
        FROM venues AS venue
        GROUP BY COALESCE(venue.timezone, 'Unknown')
        ORDER BY venue_count DESC, timezone
        """,
    )


def complexes_with_multiple_venues(
    connectable: Connectable = None,
) -> pd.DataFrame:
    """List complexes that contain more than one venue."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            complex.complex_id,
            complex.complex_name,
            COUNT(venue.venue_id) AS venue_count
        FROM complexes AS complex
        JOIN venues AS venue
            ON venue.complex_id = complex.complex_id
        GROUP BY complex.complex_id, complex.complex_name
        HAVING COUNT(venue.venue_id) > 1
        ORDER BY venue_count DESC, complex.complex_name
        """,
    )


def venue_counts_by_country(connectable: Connectable = None) -> pd.DataFrame:
    """Count venues by country."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            COALESCE(venue.country_name, 'Unknown') AS country_name,
            COALESCE(venue.country_code, 'Unknown') AS country_code,
            COUNT(*) AS venue_count
        FROM venues AS venue
        GROUP BY
            COALESCE(venue.country_name, 'Unknown'),
            COALESCE(venue.country_code, 'Unknown')
        ORDER BY venue_count DESC, country_name
        """,
    )


def venues_by_complex(
    complex_name: str,
    connectable: Connectable = None,
) -> pd.DataFrame:
    """List venues for a specific complex name."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            venue.venue_id,
            venue.venue_name,
            venue.city_name,
            venue.country_name,
            venue.country_code,
            venue.timezone,
            complex.complex_id,
            complex.complex_name
        FROM venues AS venue
        JOIN complexes AS complex
            ON complex.complex_id = venue.complex_id
        WHERE complex.complex_name = :complex_name
        ORDER BY venue.venue_name
        """,
        {"complex_name": complex_name},
    )


def competitors_with_rankings(connectable: Connectable = None) -> pd.DataFrame:
    """List competitors with current rank, points, and movement."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            competitor.competitor_id,
            CASE
                WHEN CHARINDEX(',', competitor.name) > 0
                THEN LTRIM(SUBSTRING(competitor.name, CHARINDEX(',', competitor.name) + 1, LEN(competitor.name)))
                     + ' '
                     + LTRIM(SUBSTRING(competitor.name, 1, CHARINDEX(',', competitor.name) - 1))
                ELSE competitor.name
            END AS name,
            competitor.country,
            competitor.country_code,
            competitor.abbreviation,
            ranking.rank,
            ranking.points,
            ranking.movement,
            ranking.competitions_played,
            competitor.gender
        FROM competitors AS competitor
        JOIN competitor_rankings AS ranking
            ON ranking.competitor_id = competitor.competitor_id
        ORDER BY ranking.rank, competitor.name
        """,
    )


def top_five_ranked_competitors(connectable: Connectable = None) -> pd.DataFrame:
    """List the five best ranked competitors."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            competitor.competitor_id,
            competitor.name,
            competitor.country,
            ranking.rank,
            ranking.points,
            ranking.movement
        FROM competitors AS competitor
        JOIN competitor_rankings AS ranking
            ON ranking.competitor_id = competitor.competitor_id
        ORDER BY ranking.rank, ranking.points DESC, competitor.name
        LIMIT 5
        """,
    )


def stable_rank_movement_competitors(
    connectable: Connectable = None,
) -> pd.DataFrame:
    """List competitors whose current ranking movement is stable."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            competitor.competitor_id,
            competitor.name,
            competitor.country,
            ranking.rank,
            ranking.points,
            ranking.movement
        FROM competitors AS competitor
        JOIN competitor_rankings AS ranking
            ON ranking.competitor_id = competitor.competitor_id
        WHERE ranking.movement = 0
        ORDER BY ranking.rank, competitor.name
        """,
    )


def total_points_by_country(
    country_name: str,
    connectable: Connectable = None,
) -> pd.DataFrame:
    """Return total ranking points for a specific competitor country."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            competitor.country,
            competitor.country_code,
            COUNT(competitor.competitor_id) AS competitor_count,
            COALESCE(SUM(ranking.points), 0) AS total_points
        FROM competitors AS competitor
        JOIN competitor_rankings AS ranking
            ON ranking.competitor_id = competitor.competitor_id
        WHERE competitor.country = :country_name
        GROUP BY competitor.country, competitor.country_code
        ORDER BY total_points DESC
        """,
        {"country_name": country_name},
    )


def competitor_counts_by_country(connectable: Connectable = None) -> pd.DataFrame:
    """Count competitors grouped by country."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            COALESCE(competitor.country, 'Unknown') AS country,
            COALESCE(competitor.country_code, 'Unknown') AS country_code,
            COUNT(*) AS competitor_count
        FROM competitors AS competitor
        GROUP BY
            COALESCE(competitor.country, 'Unknown'),
            COALESCE(competitor.country_code, 'Unknown')
        ORDER BY competitor_count DESC, country
        """,
    )


def highest_points_current_week(connectable: Connectable = None) -> pd.DataFrame:
    """Return competitors tied for highest points in the loaded ranking snapshot."""
    return _read_dataframe(
        connectable,
        """
        SELECT
            competitor.competitor_id,
            competitor.name,
            competitor.country,
            ranking.rank,
            ranking.points,
            ranking.competitions_played
        FROM competitors AS competitor
        JOIN competitor_rankings AS ranking
            ON ranking.competitor_id = competitor.competitor_id
        WHERE ranking.points = (
            SELECT MAX(current_ranking.points)
            FROM competitor_rankings AS current_ranking
        )
        ORDER BY ranking.rank, competitor.name
        """,
    )


def _read_dataframe(
    connectable: Connectable,
    query: str,
    params: SqlParams = None,
) -> pd.DataFrame:
    """Execute parameterized SQL and return a DataFrame."""
    engine, dispose_engine = _resolve_engine(connectable)
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(text(query), connection, params=params)
    finally:
        if dispose_engine:
            engine.dispose()


def _resolve_engine(connectable: Connectable) -> tuple[Engine, bool]:
    """Resolve an engine from an explicit connectable or DATABASE_URL."""
    if isinstance(connectable, Engine):
        return connectable, False
    if isinstance(connectable, Connection):
        return connectable.engine, False

    database_url = connectable or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "Provide a database URL/Engine or set the DATABASE_URL environment variable."
        )
    from tennis_etl.database import build_engine
    return build_engine(database_url), True
