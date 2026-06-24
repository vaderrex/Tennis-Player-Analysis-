"""
Tennis Rankings Star Schema ETL Loader
======================================
Transforms raw rankings data from staging into the star schema fact and dimension tables.
Implements Slowly Changing Dimension (SCD) Type 2 for competitor and competition history.

Usage:
    from tennis_etl.star_schema_loader import StarSchemaLoader
    
    loader = StarSchemaLoader(database_url='postgresql://...')
    loader.load_rankings(ranking_date='2026-06-02', batch_id='BATCH_20260602')
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Tuple

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class ETLStats:
    """Track ETL execution statistics."""
    
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_failed: int = 0
    dimensions_created: int = 0
    facts_loaded: int = 0
    execution_time_seconds: float = 0.0


class StarSchemaLoader:
    """
    Loads transformed data into Tennis Rankings Star Schema.
    
    Handles:
    - SCD Type 2 dimension upserts (Competitor, Competition)
    - Fact table inserts with referential integrity
    - Audit trail and batch tracking
    """
    
    def __init__(self, database_url: str, schema: str = 'dbo'):
        """
        Initialize the loader.
        
        Args:
            database_url: SQLAlchemy connection string
            schema: Schema name (SQL Server uses 'dbo')
        """
        self.database_url = database_url
        self.schema = schema
        from tennis_etl.database import build_engine
        self.engine = build_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.stats = ETLStats()
        
    def load_rankings(
        self,
        ranking_date: date | str,
        batch_id: str,
        source_system: str = 'SportRadar',
    ) -> ETLStats:
        """
        Execute full ETL pipeline to load rankings into star schema.
        
        Args:
            ranking_date: Date of rankings snapshot (YYYY-MM-DD)
            batch_id: Batch identifier for audit trail
            source_system: Source system name
            
        Returns:
            ETLStats with execution details
        """
        if isinstance(ranking_date, str):
            ranking_date = datetime.strptime(ranking_date, '%Y-%m-%d').date()
        
        start_time = datetime.now()
        
        try:
            with self.SessionLocal() as session:
                logger.info(f"Starting ETL for {ranking_date} (Batch: {batch_id})")
                
                # Step 1: Populate staging from warehouse
                self._populate_staging_from_warehouse(session, ranking_date, batch_id, source_system)
                
                # Step 2: Ensure time dimension exists
                self._ensure_time_dimension(session, ranking_date)
                
                # Step 2.5: Upsert country dimension from warehouse
                self._upsert_countries(session, source_system)
                
                # Step 3: Upsert competitor dimension from staging
                self._upsert_competitors_scd2(session, ranking_date, batch_id, source_system)
                
                # Step 4: Upsert category dimension from staging
                self._upsert_categories(session, ranking_date, batch_id, source_system)
                
                # Step 4.5: Upsert competition dimension from warehouse
                self._upsert_competitions_scd2(session, ranking_date, batch_id, source_system)
                
                # Step 5: Load fact table from staging
                self._load_fact_rankings(session, ranking_date, batch_id, source_system)
                
                # Step 6: Data quality validation
                validation_errors = self._validate_data_quality(session)
                if validation_errors:
                    logger.warning(f"Data quality warnings: {validation_errors}")
                
                session.commit()
                logger.info(f"ETL completed successfully. Stats: {self.stats}")
                
        except Exception as e:
            logger.error(f"ETL failed: {str(e)}")
            self.stats.rows_failed += 1
            raise
        finally:
            self.stats.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        
        return self.stats
    
    def _populate_staging_from_warehouse(
        self,
        session: Session,
        ranking_date: date,
        batch_id: str,
        source_system: str,
    ) -> None:
        """
        Populate STG_Rankings_Raw from warehouse tables (competitor_rankings, competitors, categories).
        This bridges the gap between warehouse and star schema.
        """
        logger.info("Populating staging table from warehouse...")
        
        # Get ranking data from warehouse and insert into staging
        warehouse_insert_sql = f"""
            INSERT INTO {self.schema}.STG_Rankings_Raw (
                CompetitorSID, CompetitorName, CategorySID, Rank, Points,
                CompetitionsPlayed, Movement, IsProcessedFlag, SourceSystem,
                ExtractedAt, LoadedAt
            )
            SELECT
                c.competitor_id,
                c.name,
                cat.category_id,
                cr.rank,
                cr.points,
                cr.competitions_played,
                cr.movement,
                'N',
                :source_system,
                GETUTCDATE(),
                :ranking_date
            FROM competitor_rankings cr
            INNER JOIN competitors c ON cr.competitor_id = c.competitor_id
            CROSS JOIN categories cat
            WHERE cr.rank IS NOT NULL
        """
        
        result = session.execute(
            text(warehouse_insert_sql),
            {
                'source_system': source_system,
                'ranking_date': ranking_date,
            }
        )
        
        rows_staged = result.rowcount
        logger.info(f"Staging populated: {rows_staged} records")
        self.stats.rows_inserted += rows_staged
    
    def _ensure_time_dimension(self, session: Session, ranking_date: date) -> None:
        """Ensure time dimension record exists for ranking date."""
        time_key = int(ranking_date.strftime('%Y%m%d'))
        
        existing = session.execute(
            text(f'SELECT COUNT(*) FROM {self.schema}.DIM_Time WHERE TimeKey = :tk'),
            {'tk': time_key}
        ).scalar()
        
        if existing == 0:
            day_of_week = ranking_date.isoweekday()  # ISO: Monday=1, Sunday=7
            is_weekend = 'Y' if day_of_week >= 6 else 'N'
            
            sql = f"""
                INSERT INTO {self.schema}.DIM_Time (
                    TimeKey, FullDate, Year, Quarter, Month, Week, Day, 
                    DayOfWeek, DayName, IsWeekend, WeekStartDate, 
                    MonthStartDate, QuarterStartDate, YearStartDate, SourceSystem
                )
                VALUES (
                    :time_key, :full_date, :year, :quarter, :month, :week, :day,
                    :dow, :day_name, :is_weekend, :week_start, :month_start, 
                    :quarter_start, :year_start, :source_system
                )
            """
            
            params = {
                'time_key': time_key,
                'full_date': ranking_date,
                'year': ranking_date.year,
                'quarter': (ranking_date.month - 1) // 3 + 1,
                'month': ranking_date.month,
                'week': ranking_date.isocalendar()[1],
                'day': ranking_date.day,
                'dow': day_of_week,
                'day_name': ranking_date.strftime('%A'),
                'is_weekend': is_weekend,
                'week_start': ranking_date.replace(day=1),  # Simplified; use proper logic
                'month_start': ranking_date.replace(day=1),
                'quarter_start': ranking_date.replace(month=(ranking_date.month-1)//3*3+1, day=1),
                'year_start': ranking_date.replace(month=1, day=1),
                'source_system': 'SYSTEM',
            }
            
            session.execute(text(sql), params)
            logger.info(f"Time dimension created for {ranking_date}")
    
    def _upsert_competitors_scd2(
        self,
        session: Session,
        ranking_date: date,
        batch_id: str,
        source_system: str,
    ) -> None:
        """
        Upsert competitors using SCD Type 2 logic from staging.
        
        - If competitor exists with same name, country, and abbreviation: no change
        - If competitor exists but attributes changed: close old version, create new
        - If competitor is new: insert with EffectiveDate = ranking_date
        """
        logger.debug("Upserting competitors from staging...")
        
        sql = f"""
            SELECT DISTINCT
                sr.CompetitorSID,
                sr.CompetitorName,
                c.country_code,
                c.abbreviation
            FROM {self.schema}.STG_Rankings_Raw sr
            LEFT JOIN {self.schema}.competitors c ON sr.CompetitorSID = c.competitor_id
            WHERE sr.IsProcessedFlag = 'N'
              AND CAST(sr.LoadedAt AS DATE) = :ranking_date
        """
        
        competitors = session.execute(
            text(sql),
            {'ranking_date': ranking_date}
        ).fetchall()
        
        for comp_sid, comp_name, country_code, abbreviation in competitors:
            # Normalize "Last, First" → "First Last"
            if comp_name and ',' in comp_name:
                parts = comp_name.split(',', 1)
                comp_name = f"{parts[1].strip()} {parts[0].strip()}"
            # Clean values
            country_code = country_code.strip() if country_code else None
            abbreviation = abbreviation.strip() if abbreviation else None
            country_key = self._hash_to_bigint(country_code) if country_code else None
            
            # Check if current version exists
            check_sql = f"""
                SELECT CompetitorKey, CompetitorName, CountryCode, Abbreviation
                FROM {self.schema}.DIM_Competitor
                WHERE CompetitorSID = :sid AND IsCurrentFlag = 'Y'
            """
            
            current = session.execute(
                text(check_sql),
                {'sid': comp_sid}
            ).fetchone()
            
            if current is None:
                # New competitor: INSERT with generated key
                comp_key = self._hash_to_bigint(comp_sid)
                insert_sql = f"""
                    INSERT INTO {self.schema}.DIM_Competitor (
                        CompetitorKey, CompetitorSID, CompetitorName, 
                        CountryKey, CountryCode, Abbreviation,
                        EffectiveDate, IsCurrentFlag, SourceSystem, ETLBatchID
                    )
                    VALUES (:key, :sid, :name, :country_key, :country_code, :abbrev, :eff_date, 'Y', :source_sys, :batch_id)
                """
                
                session.execute(
                    text(insert_sql),
                    {
                        'key': comp_key,
                        'sid': comp_sid,
                        'name': comp_name,
                        'country_key': country_key,
                        'country_code': country_code,
                        'abbrev': abbreviation,
                        'eff_date': ranking_date,
                        'source_sys': source_system,
                        'batch_id': batch_id,
                    }
                )
                self.stats.dimensions_created += 1
                logger.debug(f"Competitor inserted: {comp_sid}")
            
            elif (current[1] != comp_name or 
                  current[2] != country_code or 
                  current[3] != abbreviation):
                # Changed: Close old, create new version
                comp_key_old = current[0]
                comp_key_new = self._hash_to_bigint(comp_sid + str(ranking_date))
                
                close_sql = f"""
                    UPDATE {self.schema}.DIM_Competitor
                    SET IsCurrentFlag = 'N', ExpiryDate = :exp_date
                    WHERE CompetitorKey = :key
                """
                
                session.execute(
                    text(close_sql),
                    {'key': comp_key_old, 'exp_date': ranking_date}
                )
                
                reasons = []
                if current[1] != comp_name:
                    reasons.append("Name changed")
                if current[2] != country_code:
                    reasons.append("Country changed")
                if current[3] != abbreviation:
                    reasons.append("Abbreviation changed")
                reason = ", ".join(reasons)
                
                insert_sql = f"""
                    INSERT INTO {self.schema}.DIM_Competitor (
                        CompetitorKey, CompetitorSID, CompetitorName,
                        CountryKey, CountryCode, Abbreviation,
                        EffectiveDate, IsCurrentFlag, ChangeReason, SourceSystem, ETLBatchID
                    )
                    VALUES (:key, :sid, :name, :country_key, :country_code, :abbrev, :eff_date, 'Y', :reason, :source_sys, :batch_id)
                """
                
                session.execute(
                    text(insert_sql),
                    {
                        'key': comp_key_new,
                        'sid': comp_sid,
                        'name': comp_name,
                        'country_key': country_key,
                        'country_code': country_code,
                        'abbrev': abbreviation,
                        'eff_date': ranking_date,
                        'reason': reason,
                        'source_sys': source_system,
                        'batch_id': batch_id,
                    }
                )
                self.stats.dimensions_created += 1
                logger.debug(f"Competitor version created: {comp_sid}")

    def _upsert_countries(self, session: Session, source_system: str) -> None:
        """
        Extract countries from warehouse competitors and venues, clean them,
        and upsert into DIM_Country.
        """
        logger.info("Upserting countries from warehouse competitors and venues...")
        
        # Get unique country code and country name combinations from competitors and venues
        sql = """
            SELECT DISTINCT country_code, country_name
            FROM (
                SELECT country_code, country AS country_name FROM competitors WHERE country_code IS NOT NULL AND country IS NOT NULL
                UNION
                SELECT country_code, country_name FROM venues WHERE country_code IS NOT NULL AND country_name IS NOT NULL
            ) AS t
        """
        res = session.execute(text(sql)).fetchall()
        
        from collections import defaultdict
        by_code = defaultdict(list)
        for code, name in res:
            if code and name:
                by_code[code.strip().upper()].append(name.strip())
                
        for code, names in by_code.items():
            cleaned_names = []
            for name in names:
                name = name.replace('\ufffd', "'")
                name = name.replace('\u00ef\u00bf\u00bd', "'")
                if name.isupper():
                    name = name.title()
                cleaned_names.append(name)
            
            # Filter out name equal to code
            filtered_names = [n for n in cleaned_names if n.upper() != code]
            if not filtered_names:
                filtered_names = cleaned_names
                
            best_name = max(filtered_names, key=len)
            if best_name in ["Cote D'Ivoire", "Cote D' Ivoire", "Cote D Ivoire"]:
                best_name = "Cote d'Ivoire"
                
            country_key = self._hash_to_bigint(code)
            
            # Upsert into DIM_Country
            check_sql = f"""
                SELECT CountryKey FROM {self.schema}.DIM_Country WHERE CountryCode = :code
            """
            existing = session.execute(text(check_sql), {'code': code}).fetchone()
            
            if existing is None:
                insert_sql = f"""
                    INSERT INTO {self.schema}.DIM_Country (
                        CountryKey, CountryCode, CountryName, Region, SubRegion, IsActiveFlag, SourceSystem
                    )
                    VALUES (:key, :code, :name, NULL, NULL, 'Y', :source_sys)
                """
                session.execute(
                    text(insert_sql),
                    {
                        'key': country_key,
                        'code': code,
                        'name': best_name,
                        'source_sys': source_system
                    }
                )
                self.stats.dimensions_created += 1
            else:
                update_sql = f"""
                    UPDATE {self.schema}.DIM_Country
                    SET CountryName = :name, SourceSystem = :source_sys, UpdatedAt = GETUTCDATE()
                    WHERE CountryCode = :code
                """
                session.execute(
                    text(update_sql),
                    {
                        'code': code,
                        'name': best_name,
                        'source_sys': source_system
                    }
                )
    
    def _upsert_categories(
        self,
        session: Session,
        ranking_date: date,
        batch_id: str,
        source_system: str,
    ) -> None:
        """
        Upsert categories from warehouse categories table.
        """
        logger.debug("Upserting categories...")
        
        # Get distinct categories from staging
        sql = f"""
            SELECT DISTINCT
                sr.CategorySID
            FROM {self.schema}.STG_Rankings_Raw sr
            WHERE sr.IsProcessedFlag = 'N'
              AND CAST(sr.LoadedAt AS DATE) = :ranking_date
        """
        
        categories = session.execute(
            text(sql),
            {'ranking_date': ranking_date}
        ).fetchall()
        
        for cat_sid, in categories:
            # Check if category exists
            check_sql = f"""
                SELECT COUNT(*)
                FROM {self.schema}.DIM_Category
                WHERE CategorySID = :sid
            """
            
            exists = session.execute(
                text(check_sql),
                {'sid': cat_sid}
            ).scalar()
            
            if exists == 0:
                # Get category name from warehouse
                cat_name_sql = """
                    SELECT category_name FROM categories WHERE category_id = :sid
                """
                
                cat_name_result = session.execute(
                    text(cat_name_sql),
                    {'sid': cat_sid}
                ).scalar()
                
                cat_name = cat_name_result or cat_sid
                cat_key = self._hash_to_bigint(cat_sid)
                
                # Insert category
                insert_sql = f"""
                    INSERT INTO {self.schema}.DIM_Category (
                        CategoryKey, CategorySID, CategoryName, IsProFlag, SourceSystem
                    )
                    VALUES (:key, :sid, :name, 'Y', :source_sys)
                """
                
                session.execute(
                    text(insert_sql),
                    {
                        'key': cat_key,
                        'sid': cat_sid,
                        'name': cat_name,
                        'source_sys': source_system,
                    }
                )
                self.stats.dimensions_created += 1
                logger.debug(f"Category inserted: {cat_sid}")
    
    def _upsert_competitions_scd2(
        self,
        session: Session,
        ranking_date: date,
        batch_id: str,
        source_system: str,
    ) -> None:
        """
        Upsert competitions (tournaments/events) from the warehouse competitions table
        into DIM_Competition using SCD Type 2 logic.

        - New competition: INSERT with IsCurrentFlag = 'Y'
        - Changed name/type/gender/level: close old version, insert new
        - Unchanged: skip
        """
        logger.info("Upserting competitions from warehouse into DIM_Competition...")

        sql = """
            SELECT
                comp.competition_id,
                comp.competition_name,
                comp.type,
                comp.gender,
                comp.category_id,
                comp.parent_id
            FROM competitions comp
        """
        competitions = session.execute(text(sql)).fetchall()

        for comp_sid, comp_name, comp_type, gender, category_id, parent_id in competitions:
            # Resolve CategoryKey from DIM_Category
            cat_key_row = session.execute(
                text(f"SELECT CategoryKey FROM {self.schema}.DIM_Category WHERE CategorySID = :sid"),
                {'sid': category_id}
            ).fetchone()

            if cat_key_row is None:
                logger.warning(f"Category {category_id} not found in DIM_Category, skipping competition {comp_sid}")
                continue

            cat_key = cat_key_row[0]

            # Resolve ParentCompetitionKey (self-referencing hierarchy)
            parent_comp_key = None
            if parent_id:
                parent_row = session.execute(
                    text(f"SELECT CompetitionKey FROM {self.schema}.DIM_Competition WHERE CompetitionSID = :sid AND IsCurrentFlag = 'Y'"),
                    {'sid': parent_id}
                ).fetchone()
                if parent_row:
                    parent_comp_key = parent_row[0]

            # Normalise gender to constraint-valid value
            gender_map = {'men': 'Men', 'women': 'Women', 'mixed': 'Mixed'}
            gender_clean = gender_map.get((gender or '').lower()) if gender else None

            # Normalise competition type to constraint-valid value
            type_map = {'singles': 'Singles', 'doubles': 'Doubles', 'mixed': 'Mixed'}
            type_clean = type_map.get((comp_type or '').lower()) if comp_type else None

            # Check if a current version already exists
            check_sql = f"""
                SELECT CompetitionKey, CompetitionName, CompetitionType, Gender
                FROM {self.schema}.DIM_Competition
                WHERE CompetitionSID = :sid AND IsCurrentFlag = 'Y'
            """
            current = session.execute(text(check_sql), {'sid': comp_sid}).fetchone()

            if current is None:
                # New competition — insert
                comp_key = self._hash_to_bigint(comp_sid)
                insert_sql = f"""
                    INSERT INTO {self.schema}.DIM_Competition (
                        CompetitionKey, CompetitionSID, CompetitionName,
                        CompetitionType, Gender, CategoryKey, ParentCompetitionKey,
                        IsTeamCompetitionFlag, EffectiveDate, IsCurrentFlag,
                        SourceSystem, SourceRecordID
                    )
                    VALUES (:key, :sid, :name, :comp_type, :gender, :cat_key, :parent_key,
                            'N', :eff_date, 'Y', :source_sys, :src_record_id)
                """
                session.execute(
                    text(insert_sql),
                    {
                        'key': comp_key,
                        'sid': comp_sid,
                        'name': comp_name,
                        'comp_type': type_clean,
                        'gender': gender_clean,
                        'cat_key': cat_key,
                        'parent_key': parent_comp_key,
                        'eff_date': ranking_date,
                        'source_sys': source_system,
                        'src_record_id': comp_sid,
                    }
                )
                self.stats.dimensions_created += 1
                logger.debug(f"Competition inserted: {comp_sid} ({comp_name})")

            else:
                # Check if attributes have changed
                current_key, current_name, current_type, current_gender = current
                changed = (
                    current_name != comp_name
                    or current_type != type_clean
                    or current_gender != gender_clean
                )

                if changed:
                    reasons = []
                    if current_name != comp_name:
                        reasons.append("Name changed")
                    if current_type != type_clean:
                        reasons.append("Type changed")
                    if current_gender != gender_clean:
                        reasons.append("Gender changed")
                    reason = ", ".join(reasons)

                    # Close old version
                    session.execute(
                        text(f"""
                            UPDATE {self.schema}.DIM_Competition
                            SET IsCurrentFlag = 'N', ExpiryDate = :exp_date
                            WHERE CompetitionKey = :key
                        """),
                        {'key': current_key, 'exp_date': ranking_date}
                    )

                    # Insert new version
                    new_key = self._hash_to_bigint(comp_sid + str(ranking_date))
                    session.execute(
                        text(f"""
                            INSERT INTO {self.schema}.DIM_Competition (
                                CompetitionKey, CompetitionSID, CompetitionName,
                                CompetitionType, Gender, CategoryKey, ParentCompetitionKey,
                                IsTeamCompetitionFlag, EffectiveDate, IsCurrentFlag,
                                ChangeReason, SourceSystem, SourceRecordID
                            )
                            VALUES (:key, :sid, :name, :comp_type, :gender, :cat_key, :parent_key,
                                    'N', :eff_date, 'Y', :reason, :source_sys, :src_record_id)
                        """),
                        {
                            'key': new_key,
                            'sid': comp_sid,
                            'name': comp_name,
                            'comp_type': type_clean,
                            'gender': gender_clean,
                            'cat_key': cat_key,
                            'parent_key': parent_comp_key,
                            'eff_date': ranking_date,
                            'reason': reason,
                            'source_sys': source_system,
                            'src_record_id': comp_sid,
                        }
                    )
                    self.stats.dimensions_created += 1
                    logger.debug(f"Competition version updated: {comp_sid} ({reason})")

        logger.info(f"DIM_Competition upsert complete. Total dimensions created: {self.stats.dimensions_created}")

    def _load_fact_rankings(
        self,
        session: Session,
        ranking_date: date,
        batch_id: str,
        source_system: str,
    ) -> None:
        """Load fact table from staging with dimension lookups."""
        logger.info("Loading facts from staging...")
        
        time_key = int(ranking_date.strftime('%Y%m%d'))
        
        # Get default ranking series
        ranking_series_sql = f"""
            SELECT TOP 1 RankingSeriesKey
            FROM {self.schema}.DIM_RankingSeries
            WHERE IsActiveFlag = 'Y'
            ORDER BY EffectiveDate DESC
        """
        
        ranking_series_key = session.execute(text(ranking_series_sql)).scalar()
        
        if ranking_series_key is None:
            # Create default series
            insert_series_sql = f"""
                INSERT INTO {self.schema}.DIM_RankingSeries (
                    SeriesSID, SeriesName, SeriesType, SourceSystem, IsActiveFlag, EffectiveDate
                )
                VALUES ('SR_DEFAULT', 'Default Rankings Series', 'Current', :source_sys, 'Y', :eff_date)
            """
            
            session.execute(
                text(insert_series_sql),
                {'source_sys': source_system, 'eff_date': ranking_date}
            )
            
            ranking_series_key = session.execute(text(ranking_series_sql)).scalar()
        
        # Insert fact records with proper dimension joins
        fact_insert_sql = f"""
            INSERT INTO {self.schema}.FACT_Rankings (
                CompetitorKey, RankingSeriesKey, TimeKey, CategoryKey,
                Rank, Points, CompetitionsPlayed, RankMovement,
                IsCurrentFlag, SourceSystem, ExtractedAt, LoadedAt, ETLBatchID
            )
            SELECT
                dc.CompetitorKey,
                :ranking_series_key,
                :time_key,
                dcat.CategoryKey,
                sr.Rank,
                sr.Points,
                sr.CompetitionsPlayed,
                sr.Movement,
                'Y',
                sr.SourceSystem,
                sr.ExtractedAt,
                GETUTCDATE(),
                :batch_id
            FROM {self.schema}.STG_Rankings_Raw sr
            INNER JOIN {self.schema}.DIM_Competitor dc 
                ON sr.CompetitorSID = dc.CompetitorSID AND dc.IsCurrentFlag = 'Y'
            INNER JOIN {self.schema}.DIM_Category dcat 
                ON sr.CategorySID = dcat.CategorySID
            WHERE sr.IsProcessedFlag = 'N'
              AND CAST(sr.LoadedAt AS DATE) = :ranking_date
        """
        
        result = session.execute(
            text(fact_insert_sql),
            {
                'ranking_series_key': ranking_series_key,
                'time_key': time_key,
                'ranking_date': ranking_date,
                'batch_id': batch_id,
            }
        )
        
        self.stats.facts_loaded = result.rowcount
        logger.info(f"Fact records loaded: {self.stats.facts_loaded}")
        
        # Mark staging as processed
        mark_processed_sql = f"""
            UPDATE {self.schema}.STG_Rankings_Raw
            SET IsProcessedFlag = 'Y'
            WHERE IsProcessedFlag = 'N'
              AND CAST(LoadedAt AS DATE) = :ranking_date
        """
        
        session.execute(
            text(mark_processed_sql),
            {'ranking_date': ranking_date}
        )
    
    def _validate_data_quality(self, session: Session) -> list[str]:
        """Execute data quality checks."""
        errors = []
        
        # Check for orphaned fact records
        orphan_sql = f"""
            SELECT COUNT(*)
            FROM {self.schema}.FACT_Rankings fr
            WHERE NOT EXISTS (
                SELECT 1 FROM {self.schema}.DIM_Competitor 
                WHERE CompetitorKey = fr.CompetitorKey
            )
        """
        
        orphan_count = session.execute(text(orphan_sql)).scalar()
        if orphan_count > 0:
            errors.append(f"Orphaned fact records: {orphan_count}")
        
        # Check for invalid ranks
        invalid_rank_sql = f"""
            SELECT COUNT(*)
            FROM {self.schema}.FACT_Rankings
            WHERE Rank <= 0
        """
        
        invalid_count = session.execute(text(invalid_rank_sql)).scalar()
        if invalid_count > 0:
            errors.append(f"Invalid ranks: {invalid_count}")
        
        return errors
    
    @staticmethod
    def _hash_to_bigint(value: str) -> int:
        """
        Convert string to INT via hash.
        
        Args:
            value: String to hash
            
        Returns:
            INT value (32-bit integer, positive range)
        """
        import hashlib
        hash_hex = hashlib.md5(value.encode()).hexdigest()[:8]
        # Convert first 8 hex chars to INT (max 2147483647 for positive INT)
        return int(hash_hex, 16) % (2**31 - 1)


# ============================================================================
# COMMAND-LINE USAGE
# ============================================================================

if __name__ == '__main__':
    import sys
    from datetime import datetime
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s'
    )
    
    # Example usage
    database_url = 'mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server'
    
    loader = StarSchemaLoader(database_url)
    
    # Load rankings for a specific date
    today = datetime.now().date()
    batch_id = today.strftime('%Y%m%d') + '_BATCH'
    
    try:
        stats = loader.load_rankings(
            ranking_date=today,
            batch_id=batch_id,
            source_system='SportRadar'
        )
        
        print("\n" + "="*60)
        print("ETL EXECUTION SUMMARY")
        print("="*60)
        print(f"Batch ID: {batch_id}")
        print(f"Ranking Date: {today}")
        print(f"Dimensions Created: {stats.dimensions_created}")
        print(f"Facts Loaded: {stats.facts_loaded}")
        print(f"Rows Inserted: {stats.rows_inserted}")
        print(f"Rows Updated: {stats.rows_updated}")
        print(f"Rows Skipped: {stats.rows_skipped}")
        print(f"Rows Failed: {stats.rows_failed}")
        print(f"Execution Time: {stats.execution_time_seconds:.2f}s")
        print("="*60)
        
    except Exception as e:
        logger.error(f"ETL execution failed: {str(e)}")
        sys.exit(1)
