"""Database creation and dialect-aware upsert helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Engine, Table, create_engine
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from tennis_etl.models import Base

LOGGER = logging.getLogger(__name__)
Row = Mapping[str, Any]


def build_engine(database_url: str) -> Engine:
    """Build an engine with connection health checks enabled."""
    return create_engine(database_url, pool_pre_ping=True)


def create_schema(engine: Engine) -> None:
    """Create the six ETL tables if they do not exist."""
    Base.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a SQLAlchemy session factory for the configured engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def upsert_rows(
    session: Session,
    table: Table,
    rows: Iterable[Row],
    conflict_columns: list[str],
    update_columns: list[str],
) -> int:
    """Insert rows and update existing rows for PostgreSQL or MySQL."""
    materialized_rows = list(rows)
    if not materialized_rows:
        return 0

    try:
        dialect = session.bind.dialect.name if session.bind else ""
        if dialect == "postgresql":
            statement = postgresql_insert(table).values(materialized_rows)
            excluded = statement.excluded
            statement = statement.on_conflict_do_update(
                index_elements=conflict_columns,
                set_={column: getattr(excluded, column) for column in update_columns},
            )
            session.execute(statement)
        elif dialect in {"mysql", "mariadb"}:
            statement = mysql_insert(table).values(materialized_rows)
            inserted = statement.inserted
            statement = statement.on_duplicate_key_update(
                **{column: getattr(inserted, column) for column in update_columns}
            )
            session.execute(statement)
        else:
            _merge_rows(session, table, materialized_rows, conflict_columns)
    except IntegrityError:
        session.rollback()
        LOGGER.exception("Database constraint failed while upserting %s.", table.name)
        raise
    except SQLAlchemyError:
        session.rollback()
        LOGGER.exception("Database error while upserting %s.", table.name)
        raise

    return len(materialized_rows)


def _merge_rows(
    session: Session,
    table: Table,
    rows: list[Row],
    conflict_columns: list[str],
) -> None:
    """Fallback upsert for non-PostgreSQL/MySQL development databases."""
    for row in rows:
        lookup = {column: row[column] for column in conflict_columns}
        existing = session.execute(table.select().filter_by(**lookup)).first()
        if existing:
            session.execute(table.update().filter_by(**lookup).values(**row))
        else:
            session.execute(table.insert().values(**row))
