"""Database creation and dialect-aware upsert helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Engine, Table, create_engine, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from tennis_etl.models import Base

LOGGER = logging.getLogger(__name__)
Row = Mapping[str, Any]


def build_engine(database_url: str) -> Engine:
    """Build an engine with connection health checks enabled."""
    # SQL Server specific configurations
    if "mssql" in database_url.lower():
        import pyodbc
        from urllib.parse import parse_qs, unquote, urlparse

        parsed = urlparse(database_url)
        server = unquote(parsed.hostname or "localhost")
        database = (parsed.path or "/master").lstrip("/")
        query_params = parse_qs(parsed.query)
        driver = query_params.get("driver", ["ODBC Driver 17 for SQL Server"])[0]
        trusted = query_params.get("trusted_connection", ["no"])[0]

        # Use lpc: (shared memory) protocol to connect to local SQL Server
        # instances that don't have TCP/IP or Named Pipes enabled.
        odbc_conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER=lpc:{server};"
            f"DATABASE={database};"
            f"Trusted_Connection={trusted}"
        )
        LOGGER.debug("ODBC connection string: %s", odbc_conn_str)

        def creator():
            return pyodbc.connect(odbc_conn_str)

        return create_engine(
            "mssql+pyodbc://",
            creator=creator,
            pool_pre_ping=True,
            fast_executemany=True,  # Optimize bulk inserts for SQL Server
            pool_size=10,
            max_overflow=20,
        )
    return create_engine(database_url, pool_pre_ping=True)


def create_schema(engine: Engine) -> None:
    """Create the warehouse tables and the star schema tables."""
    # 1. Create warehouse tables (Phase 1)
    Base.metadata.create_all(engine)
    
    # Ensure competitors table has gender column if it exists (for incremental updates)
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if 'competitors' in inspector.get_table_names():
        columns = [c['name'].lower() for c in inspector.get_columns('competitors')]
        if 'gender' not in columns:
            LOGGER.info("Adding gender column to competitors table")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE competitors ADD gender VARCHAR(40) NULL"))
                conn.commit()
    
    # 2. Create star schema tables using DDL script
    import re
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    ddl_path = project_root / "sql" / "STAR_SCHEMA_DDL.sql"
    
    if ddl_path.exists():
        LOGGER.info("Executing DDL script to initialize star schema: %s", ddl_path)
        with open(ddl_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            
        batches = re.split(r'^\s*GO\s*$', sql_content, flags=re.MULTILINE | re.IGNORECASE)
        
        with engine.connect() as conn:
            raw_conn = conn.connection.dbapi_connection
            cursor = raw_conn.cursor()
            for batch in batches:
                cleaned_batch = batch.strip()
                if cleaned_batch:
                    if cleaned_batch.upper().startswith("USE "):
                        continue
                    try:
                        cursor.execute(cleaned_batch)
                        raw_conn.commit()
                    except Exception as e:
                        # Some errors (like DROP VIEW failures or objects already existing) are normal
                        LOGGER.debug("DDL batch execution warning/error: %s", e)
    else:
        LOGGER.warning("Star schema DDL script not found at %s", ddl_path)


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
    """Insert rows and update existing rows for PostgreSQL, MySQL, or SQL Server."""
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
        elif dialect == "mssql":
            # SQL Server uses MERGE for upsert
            _merge_rows_mssql(session, table, materialized_rows, conflict_columns, update_columns)
        else:
            _merge_rows(session, table, materialized_rows, conflict_columns, update_columns)
    except IntegrityError:
        session.rollback()
        LOGGER.exception("Database constraint failed while upserting %s.", table.name)
        raise
    except SQLAlchemyError:
        session.rollback()
        LOGGER.exception("Database error while upserting %s.", table.name)
        raise

    return len(materialized_rows)


def _merge_rows_mssql(
    session: Session,
    table: Table,
    rows: list[Row],
    conflict_columns: list[str],
    update_columns: list[str],
) -> None:
    """SQL Server upsert using MERGE statement logic."""
    if not rows:
        return
    
    for row in rows:
        # Construct explicit Core WHERE clause
        where_clause = [getattr(table.c, col) == row[col] for col in conflict_columns]
        
        # Use .where() instead of .filter_by()
        existing = session.execute(table.select().where(*where_clause)).first()
        
        if existing:
            update_values = {column: row[column] for column in update_columns}
            if update_values:
                session.execute(table.update().where(*where_clause).values(**update_values))
        else:
            session.execute(table.insert().values(**row))


def _merge_rows(
    session: Session,
    table: Table,
    rows: list[Row],
    conflict_columns: list[str],
    update_columns: list[str] | None = None,
) -> None:
    """Fallback upsert for non-PostgreSQL/MySQL development databases."""
    if update_columns is None:
        update_columns = list(rows[0].keys()) if rows else []
    
    for row in rows:
        where_clause = [getattr(table.c, col) == row[col] for col in conflict_columns]
        
        existing = session.execute(table.select().where(*where_clause)).first()
        
        if existing:
            update_values = {column: row[column] for column in update_columns}
            if update_values:
                session.execute(table.update().where(*where_clause).values(**update_values))
        else:
            session.execute(table.insert().values(**row))
