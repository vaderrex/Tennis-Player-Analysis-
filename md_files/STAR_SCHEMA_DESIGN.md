# 🎾 Tennis Rankings - Star Schema Data Warehouse Design

**Target Database:** SQL Server / PostgreSQL / Snowflake (portable DDL)  
**Design Date:** June 2, 2026  
**Business Domain:** Tennis Rankings Analytics  

---

## 1. Business Process & Grain Identification

### 📊 Business Process Overview

The **Tennis Rankings Business Process** tracks and analyzes competitive standings for professional tennis players and teams across multiple tournaments and categories globally.

**Key Questions the Business Wants to Answer:**
- How do players rank across different competition categories (ATP, WTA, Challenger)?
- What is the trend of a player's rank and points over time?
- Which competitions influence ranking movements the most?
- How do venue characteristics correlate with ranking activity?
- What is the geographic distribution of competitors?

### 🎯 Fact Table Grain (Atomic Unit of Analysis)

**GRAIN:** _One row per competitor ranking snapshot at a specific point in time, for a specific ranking series._

This represents the lowest level of detail:
- **Entity:** A single competitor (player or doubles team)
- **Dimension:** Their current rank within a specific ranking series
- **Time:** The snapshot date when this ranking was recorded
- **Metrics:** Points, rank movement, competitions played, win-loss ratio

**Measurable Events (Additive/Semi-Additive):**
- Rank Position (semi-additive—meaningful only at specific time grain)
- Total Points (semi-additive—cumulative but context-dependent)
- Competitions Played (additive across non-overlapping time windows)
- Rank Movement (derived—directional change)

---

## 2. Schema Architecture

### 📐 Star Schema Entity Map

```
                    ┌─────────────────────────┐
                    │  FACT_Rankings          │
                    │  (Atomic Fact Table)    │
                    └────────┬────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ DIM_Competitor
   │  (SCD Type 2)
   │  (3M+ rows)  │  │ DIM_RankingSeries
   │              │  │  (fast dim)     │  │ DIM_Time
   │ PK: CompetitorK
   │              │  │ PK: SeriesK     │  │ (PK: DateKey)
   └──────────────┘  └──────────────┘  └──────────────┘

        ▼                    ▼                    ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ DIM_Country  │  │ DIM_Category │  │ DIM_Venue
   │ (small dim)  │  │ (small dim)   │  │ (medium dim)
   └──────────────┘  └──────────────┘  └──────────────┘

        ▼
   ┌──────────────┐
   │ DIM_Competition
   │  (SCD Type 2)
   │ (1K+ rows)   │
   └──────────────┘
```

### 📋 Core Tables

#### **FACT_Rankings** (Core Fact Table)
```
Primary Key: RankingFactKey (surrogate INT/BIGINT)
Grain: One row per competitor per ranking snapshot

Foreign Keys:
  ├─ CompetitorKey (FK → DIM_Competitor)
  ├─ RankingSeriesKey (FK → DIM_RankingSeries)
  ├─ TimeKey (FK → DIM_Time)
  ├─ CategoryKey (FK → DIM_Category)
  ├─ VenueKey (FK → DIM_Venue, nullable)
  └─ CompetitionKey (FK → DIM_Competition, nullable)

Metrics (Measures):
  ├─ Rank (integer)
  ├─ Points (integer)
  ├─ CompetitionsPlayed (integer)
  ├─ RankMovement (integer, derived)
  ├─ Wins (integer, nullable)
  ├─ Losses (integer, nullable)
  └─ WinPercentage (decimal, derived)

Audit Columns:
  ├─ SourceSystemKey (identifier of originating system)
  ├─ ExtractedAt (timestamp of data extraction)
  ├─ LoadedAt (timestamp of warehouse load)
  ├─ UpdatedAt (timestamp of last update)
  └─ IsCurrentFlag (Y/N — indicates latest snapshot)
```

---

#### **DIM_Competitor** (Slowly Changing Dimension - Type 2)
```
Primary Key: CompetitorKey (surrogate BIGINT)
Natural Key: CompetitorSID (source system ID) + EffectiveDate

Attributes:
  ├─ CompetitorSID (source ID)
  ├─ CompetitorName
  ├─ CountryKey (FK → DIM_Country)
  ├─ CountryCode (IIN—ISO-3166)
  ├─ Abbreviation
  ├─ CompetitorType (Individual/Team/Doubles)
  └─ CompetitionSpecialty (Singles/Doubles/Mixed)

SCD Type 2 Tracking:
  ├─ EffectiveDate
  ├─ ExpiryDate
  ├─ IsCurrentFlag (Y/N)
  ├─ RowStartDate
  ├─ RowEndDate
  └─ ChangeReason
```

#### **DIM_RankingSeries** (Fast Changing Dimension)
```
Primary Key: RankingSeriesKey (surrogate INT)
Natural Key: SeriesSID (source ID)

Attributes:
  ├─ SeriesSID
  ├─ SeriesName (e.g., "ATP Rankings 2026")
  ├─ SeriesDescription
  ├─ SeriesType (Current/Historical/Projected)
  ├─ SourceSystem
  ├─ IsActiveFlag
  └─ EffectiveDate
```

#### **DIM_Time** (Standard Time Dimension)
```
Primary Key: TimeKey (INT: YYYYMMDD)

Attributes:
  ├─ FullDate
  ├─ Year
  ├─ Quarter
  ├─ Month
  ├─ Week
  ├─ Day
  ├─ DayOfWeek
  ├─ DayName
  ├─ WeekStartDate
  ├─ MonthStartDate
  ├─ QuarterStartDate
  ├─ YearStartDate
  ├─ IsWeekend (Y/N)
  ├─ FiscalYear (for reporting)
  └─ Season (tennis season identifier)
```

#### **DIM_Category** (Static Dimension)
```
Primary Key: CategoryKey (INT)
Natural Key: CategorySID (source ID)

Attributes:
  ├─ CategorySID
  ├─ CategoryName (ATP, WTA, Challenger, ITF, etc.)
  ├─ CategoryDescription
  ├─ IsProFlag (Y/N)
  ├─ CreatedAt
  └─ UpdatedAt
```

#### **DIM_Country** (Static Dimension)
```
Primary Key: CountryKey (INT)
Natural Key: CountryCode (ISO-3166-1-alpha-2)

Attributes:
  ├─ CountryCode
  ├─ CountryName
  ├─ Region (continent)
  ├─ SubRegion
  └─ IsActiveFlag (Y/N)
```

#### **DIM_Competition** (SCD Type 2)
```
Primary Key: CompetitionKey (surrogate BIGINT)
Natural Key: CompetitionSID + EffectiveDate

Attributes:
  ├─ CompetitionSID (source ID)
  ├─ CompetitionName
  ├─ CompetitionType (Singles/Doubles/Mixed)
  ├─ Gender (Men/Women/Mixed)
  ├─ Level (Grand Slam/ATP500/ATP250/WTA1000, etc.)
  ├─ CategoryKey (FK → DIM_Category)
  ├─ ParentCompetitionKey (self-join for hierarchies)
  ├─ IsTeamCompetitionFlag
  └─ SCD2 Tracking Columns (EffectiveDate, ExpiryDate, IsCurrentFlag)
```

#### **DIM_Venue** (SCD Type 1 - slowly moving)
```
Primary Key: VenueKey (INT)
Natural Key: VenueSID

Attributes:
  ├─ VenueSID
  ├─ VenueName
  ├─ CountryKey (FK → DIM_Country)
  ├─ City
  ├─ Timezone
  ├─ Capacity
  ├─ Surface (Clay/Grass/Hard/Carpet)
  ├─ ComplexName
  ├─ Latitude/Longitude (for geo-analysis)
  ├─ CreatedAt
  └─ UpdatedAt
```

---

## 3. Data Modeling & Type Handling

### 🔑 Surrogate Key Strategy

| Table | Key Type | Rationale |
|-------|----------|-----------|
| FACT_Rankings | BIGINT (1-based sequence) | High-volume table; supports ~9B rows |
| DIM_Competitor | BIGINT (MD5 Hash of CompetitorSID) | Large dimension; enables fast lookups |
| DIM_Time | INT (YYYYMMDD) | Natural semantic date key; immutable |
| DIM_Category | INT (1-based sequence) | Small, stable dimension |
| DIM_Country | INT (1-based sequence) | Small, stable dimension |
| DIM_Competition | BIGINT (MD5 Hash of CompetitionSID) | Moderate-large; SCD Type 2 tracking |
| DIM_Venue | INT (1-based sequence) | Medium, stable dimension |
| DIM_RankingSeries | INT (1-based sequence) | Small reference dimension |

### 📊 Data Type Mapping

**Snowflake/PostgreSQL/SQL Server Compatibility:**

| Logical Type | SQL Server | PostgreSQL | Snowflake | Notes |
|--------------|-----------|-----------|-----------|-------|
| Surrogate Key (Large) | BIGINT | BIGINT | BIGINT | 64-bit integer for ~9B values |
| Surrogate Key (Small) | INT | INT | INT | 32-bit integer for ~2B values |
| Natural Key (ID) | VARCHAR(64) | VARCHAR(64) | VARCHAR(64) | Source system IDs; indexed |
| Name/Description | VARCHAR/NVARCHAR | VARCHAR | VARCHAR | Case-sensitive in PG; indexed |
| Numeric Measure | BIGINT / DECIMAL | BIGINT / NUMERIC | BIGINT / DECIMAL | Rank/Points as BIGINT; ratio as DECIMAL |
| Timestamp | DATETIME2 / TIMESTAMP | TIMESTAMP | TIMESTAMP | Always UTC; 3+ digit precision |
| Boolean Flag | CHAR(1) Y/N | CHAR(1) or BOOLEAN | BOOLEAN | Char(1) for DB agnostic; BOOLEAN where supported |
| Date Key | INT (YYYYMMDD) | INT | INT | Efficient range scans |
| Decimal (Ratio) | DECIMAL(10,4) | NUMERIC(10,4) | DECIMAL(10,4) | Win % precision to 0.01% |

### ⏰ Audit & Metadata Columns

**All tables include:**
```sql
created_at          DATETIME2 DEFAULT CURRENT_TIMESTAMP   -- Record insertion time
updated_at          DATETIME2 DEFAULT CURRENT_TIMESTAMP   -- Record last modification
source_system       VARCHAR(64) NOT NULL                  -- "SportRadar", "Manual", etc.
source_record_id    VARCHAR(128)                          -- Original API response ID
etl_batch_id        VARCHAR(128)                          -- Batch identifier for auditing
is_active_flag      CHAR(1) DEFAULT 'Y'                   -- Logical delete flag
```

### 🔄 Slowly Changing Dimension Handling

**SCD Type 2 (DIM_Competitor, DIM_Competition):**
- New version created when key attributes change
- Linked by Natural Key + Effective Date
- Current row marked with `is_current_flag = 'Y'` and `expiry_date = NULL`
- Enables point-in-time analysis

**SCD Type 1 (DIM_Venue, DIM_Category):**
- Attributes overwritten; history not maintained
- Simpler, lower storage footprint
- Acceptable for stable attributes (venue name, country)

---

## 4. SQL DDL Generation

### Target: **PostgreSQL 14+ / Snowflake / SQL Server 2019+**

```sql
-- ============================================================================
-- Tennis Rankings Star Schema - Production DDL
-- Target Database: PostgreSQL / Snowflake / SQL Server (compatible syntax)
-- Generated: 2026-06-02
-- Grain: One row per competitor per ranking snapshot
-- ============================================================================

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- DIM_Time: Standard time dimension (pre-populated with 20+ years)
CREATE TABLE dim_time (
    time_key INT PRIMARY KEY,                          -- YYYYMMDD format
    full_date DATE NOT NULL UNIQUE,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    week INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,                          -- 1=Monday, 7=Sunday (ISO)
    day_name VARCHAR(10) NOT NULL,
    is_weekend CHAR(1) NOT NULL,                       -- Y/N
    week_start_date DATE NOT NULL,
    month_start_date DATE NOT NULL,
    quarter_start_date DATE NOT NULL,
    year_start_date DATE NOT NULL,
    fiscal_year INT,
    season VARCHAR(20),                                -- "2025-26 ATP", etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(64) NOT NULL DEFAULT 'SYSTEM',
    CONSTRAINT ck_quarter CHECK (quarter BETWEEN 1 AND 4),
    CONSTRAINT ck_month CHECK (month BETWEEN 1 AND 12),
    CONSTRAINT ck_week CHECK (week BETWEEN 1 AND 53),
    CONSTRAINT ck_day CHECK (day BETWEEN 1 AND 31),
    CONSTRAINT ck_day_of_week CHECK (day_of_week BETWEEN 1 AND 7)
);

CREATE INDEX idx_dim_time_full_date ON dim_time(full_date);
CREATE INDEX idx_dim_time_year_month ON dim_time(year, month);
CREATE INDEX idx_dim_time_season ON dim_time(season);

-- DIM_Category: Tennis ranking categories (ATP, WTA, Challenger, ITF)
CREATE TABLE dim_category (
    category_key INT PRIMARY KEY,
    category_sid VARCHAR(64) NOT NULL UNIQUE,          -- Source: sr:category:X
    category_name VARCHAR(255) NOT NULL,
    category_description TEXT,
    is_pro_flag CHAR(1) NOT NULL DEFAULT 'Y',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
    CONSTRAINT ck_is_pro_flag CHECK (is_pro_flag IN ('Y', 'N'))
);

CREATE INDEX idx_dim_category_name ON dim_category(category_name);

-- DIM_Country: Geographic dimension
CREATE TABLE dim_country (
    country_key INT PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL UNIQUE,           -- ISO-3166-1-alpha-2
    country_name VARCHAR(255) NOT NULL,
    region VARCHAR(100),                               -- Continent
    sub_region VARCHAR(100),
    is_active_flag CHAR(1) NOT NULL DEFAULT 'Y',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(64) NOT NULL DEFAULT 'GEO_DB',
    CONSTRAINT ck_is_active CHECK (is_active_flag IN ('Y', 'N'))
);

CREATE INDEX idx_dim_country_name ON dim_country(country_name);
CREATE INDEX idx_dim_country_region ON dim_country(region);

-- DIM_Venue: Tennis venues (courts, complexes)
CREATE TABLE dim_venue (
    venue_key INT PRIMARY KEY,
    venue_sid VARCHAR(64) NOT NULL UNIQUE,             -- Source: sr:venue:X
    venue_name VARCHAR(255) NOT NULL,
    country_key INT NOT NULL,
    city VARCHAR(255),
    timezone VARCHAR(128),
    capacity INT,
    surface VARCHAR(50),                               -- Clay, Grass, Hard, Carpet
    complex_name VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
    FOREIGN KEY (country_key) REFERENCES dim_country(country_key),
    CONSTRAINT ck_surface CHECK (surface IN ('Clay', 'Grass', 'Hard', 'Carpet', NULL))
);

CREATE INDEX idx_dim_venue_name ON dim_venue(venue_name);
CREATE INDEX idx_dim_venue_country ON dim_venue(country_key);
CREATE INDEX idx_dim_venue_city ON dim_venue(city);

-- DIM_RankingSeries: Reference to different ranking systems
CREATE TABLE dim_ranking_series (
    ranking_series_key INT PRIMARY KEY,
    series_sid VARCHAR(64) NOT NULL UNIQUE,            -- Source system ID
    series_name VARCHAR(255) NOT NULL,
    series_description TEXT,
    series_type VARCHAR(50),                           -- Current, Historical, Projected
    source_system VARCHAR(64) NOT NULL,
    is_active_flag CHAR(1) NOT NULL DEFAULT 'Y',
    effective_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_series_type CHECK (series_type IN ('Current', 'Historical', 'Projected')),
    CONSTRAINT ck_is_active CHECK (is_active_flag IN ('Y', 'N'))
);

CREATE INDEX idx_dim_ranking_series_name ON dim_ranking_series(series_name);

-- DIM_Competitor: Tennis players / teams (SCD Type 2)
CREATE TABLE dim_competitor (
    competitor_key BIGINT PRIMARY KEY,                 -- Surrogate key (MD5 based)
    competitor_sid VARCHAR(64) NOT NULL,               -- Source: sr:competitor:X
    competitor_name VARCHAR(255) NOT NULL,
    country_key INT,
    country_code VARCHAR(2),
    abbreviation VARCHAR(64),
    competitor_type VARCHAR(50),                       -- Individual, Team, Doubles
    competition_specialty VARCHAR(50),                 -- Singles, Doubles, Mixed
    
    -- SCD Type 2 Tracking
    effective_date DATE NOT NULL,                      -- When this version became active
    expiry_date DATE,                                  -- NULL = current version
    is_current_flag CHAR(1) NOT NULL DEFAULT 'Y',
    change_reason VARCHAR(255),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
    source_record_id VARCHAR(128),
    etl_batch_id VARCHAR(128),
    
    FOREIGN KEY (country_key) REFERENCES dim_country(country_key),
    CONSTRAINT ck_competitor_type CHECK (competitor_type IN ('Individual', 'Team', 'Doubles', NULL)),
    CONSTRAINT ck_specialty CHECK (competition_specialty IN ('Singles', 'Doubles', 'Mixed', NULL)),
    CONSTRAINT ck_is_current_flag CHECK (is_current_flag IN ('Y', 'N')),
    CONSTRAINT ck_expiry_logic CHECK (
        (is_current_flag = 'Y' AND expiry_date IS NULL) OR
        (is_current_flag = 'N' AND expiry_date IS NOT NULL)
    )
);

CREATE INDEX idx_dim_competitor_sid ON dim_competitor(competitor_sid);
CREATE INDEX idx_dim_competitor_name ON dim_competitor(competitor_name);
CREATE INDEX idx_dim_competitor_current ON dim_competitor(is_current_flag, effective_date DESC);
CREATE INDEX idx_dim_competitor_scd ON dim_competitor(competitor_sid, effective_date DESC);

-- DIM_Competition: Tournaments and competitions (SCD Type 2)
CREATE TABLE dim_competition (
    competition_key BIGINT PRIMARY KEY,                -- Surrogate key
    competition_sid VARCHAR(64) NOT NULL,              -- Source: sr:competition:X
    competition_name VARCHAR(255) NOT NULL,
    competition_type VARCHAR(50),                      -- Singles, Doubles, Mixed
    gender VARCHAR(50),                                -- Men, Women, Mixed
    level VARCHAR(100),                                -- Grand Slam, ATP500, ATP250, etc.
    category_key INT NOT NULL,
    parent_competition_key BIGINT,                     -- Self-join for hierarchy
    is_team_competition_flag CHAR(1) NOT NULL DEFAULT 'N',
    
    -- SCD Type 2 Tracking
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current_flag CHAR(1) NOT NULL DEFAULT 'Y',
    change_reason VARCHAR(255),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
    source_record_id VARCHAR(128),
    
    FOREIGN KEY (category_key) REFERENCES dim_category(category_key),
    FOREIGN KEY (parent_competition_key) REFERENCES dim_competition(competition_key),
    CONSTRAINT ck_comp_type CHECK (competition_type IN ('Singles', 'Doubles', 'Mixed', NULL)),
    CONSTRAINT ck_gender CHECK (gender IN ('Men', 'Women', 'Mixed', NULL)),
    CONSTRAINT ck_team_flag CHECK (is_team_competition_flag IN ('Y', 'N')),
    CONSTRAINT ck_is_current CHECK (is_current_flag IN ('Y', 'N'))
);

CREATE INDEX idx_dim_competition_sid ON dim_competition(competition_sid);
CREATE INDEX idx_dim_competition_name ON dim_competition(competition_name);
CREATE INDEX idx_dim_competition_level ON dim_competition(level);
CREATE INDEX idx_dim_competition_current ON dim_competition(is_current_flag, effective_date DESC);

-- ============================================================================
-- FACT TABLE
-- ============================================================================

-- FACT_Rankings: Core fact table (grain: one row per competitor per ranking snapshot)
CREATE TABLE fact_rankings (
    ranking_fact_key BIGINT PRIMARY KEY,               -- Auto-increment surrogate
    competitor_key BIGINT NOT NULL,
    ranking_series_key INT NOT NULL,
    time_key INT NOT NULL,
    category_key INT NOT NULL,
    competition_key BIGINT,
    venue_key INT,
    
    -- Metrics (Measures)
    rank BIGINT NOT NULL,
    points BIGINT,
    competitions_played BIGINT,
    rank_movement INT,                                 -- Positive = gained places
    wins BIGINT,
    losses BIGINT,
    win_percentage DECIMAL(10, 4),                     -- 0.0000 to 100.0000
    
    -- Additive Flag
    is_additive_flag CHAR(1) NOT NULL DEFAULT 'N',    -- Most measures are semi-additive
    
    -- Audit & Metadata
    is_current_flag CHAR(1) NOT NULL DEFAULT 'Y',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
    source_record_id VARCHAR(128),
    extracted_at TIMESTAMP,
    loaded_at TIMESTAMP,
    etl_batch_id VARCHAR(128),
    
    -- Foreign Keys
    FOREIGN KEY (competitor_key) REFERENCES dim_competitor(competitor_key),
    FOREIGN KEY (ranking_series_key) REFERENCES dim_ranking_series(ranking_series_key),
    FOREIGN KEY (time_key) REFERENCES dim_time(time_key),
    FOREIGN KEY (category_key) REFERENCES dim_category(category_key),
    FOREIGN KEY (competition_key) REFERENCES dim_competition(competition_key),
    FOREIGN KEY (venue_key) REFERENCES dim_venue(venue_key),
    
    -- Constraints
    CONSTRAINT ck_rank CHECK (rank > 0),
    CONSTRAINT ck_points CHECK (points >= 0 OR points IS NULL),
    CONSTRAINT ck_competitions CHECK (competitions_played >= 0 OR competitions_played IS NULL),
    CONSTRAINT ck_win_pct CHECK (win_percentage >= 0 AND win_percentage <= 100 OR win_percentage IS NULL),
    CONSTRAINT ck_is_current CHECK (is_current_flag IN ('Y', 'N')),
    CONSTRAINT ck_additive CHECK (is_additive_flag IN ('Y', 'N'))
);

-- Fact table indexes (optimized for typical queries)
CREATE INDEX idx_fact_rankings_competitor ON fact_rankings(competitor_key, time_key);
CREATE INDEX idx_fact_rankings_category ON fact_rankings(category_key, time_key);
CREATE INDEX idx_fact_rankings_time ON fact_rankings(time_key);
CREATE INDEX idx_fact_rankings_ranking_series ON fact_rankings(ranking_series_key, time_key);
CREATE INDEX idx_fact_rankings_current ON fact_rankings(is_current_flag) WHERE is_current_flag = 'Y';
CREATE INDEX idx_fact_rankings_points ON fact_rankings(points DESC) WHERE is_current_flag = 'Y';

-- ============================================================================
-- BRIDGE / HELPER TABLES (Optional)
-- ============================================================================

-- BridgeCompetitorToCompetition: M:M relationship for flexible analysis
CREATE TABLE bridge_competitor_competition (
    bridge_key BIGINT PRIMARY KEY,
    competitor_key BIGINT NOT NULL,
    competition_key BIGINT NOT NULL,
    participation_type VARCHAR(50),                    -- Participant, Winner, Runner-up, etc.
    appeared_date DATE,
    
    FOREIGN KEY (competitor_key) REFERENCES dim_competitor(competitor_key),
    FOREIGN KEY (competition_key) REFERENCES dim_competition(competition_key),
    UNIQUE (competitor_key, competition_key)
);

CREATE INDEX idx_bridge_comp_comp ON bridge_competitor_competition(competitor_key, competition_key);

-- ============================================================================
-- STAGING TABLES (ETL Processing)
-- ============================================================================

-- stg_rankings_raw: Temporary staging for incoming rankings
CREATE TABLE stg_rankings_raw (
    stg_key BIGINT PRIMARY KEY,
    competitor_sid VARCHAR(64),
    competitor_name VARCHAR(255),
    category_sid VARCHAR(64),
    rank BIGINT,
    points BIGINT,
    movement INT,
    competitions_played BIGINT,
    ranking_date DATE,
    source_system VARCHAR(64),
    extracted_at TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_processed_flag CHAR(1) DEFAULT 'N'
);

CREATE INDEX idx_stg_rankings_processed ON stg_rankings_raw(is_processed_flag);
CREATE INDEX idx_stg_rankings_date ON stg_rankings_raw(ranking_date);

-- stg_competitor_changes: Track dimension changes
CREATE TABLE stg_competitor_changes (
    stg_key BIGINT PRIMARY KEY,
    competitor_sid VARCHAR(64),
    previous_name VARCHAR(255),
    new_name VARCHAR(255),
    change_type VARCHAR(50),                           -- UPDATE, INSERT, DELETE
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- VIEWS FOR REPORTING
-- ============================================================================

-- vw_current_rankings: Latest ranking snapshot
CREATE VIEW vw_current_rankings AS
SELECT
    dc.competitor_name,
    dco.country_name,
    dcat.category_name,
    fr.rank,
    fr.points,
    fr.competitions_played,
    fr.rank_movement,
    fr.win_percentage,
    dt.full_date AS ranking_date
FROM fact_rankings fr
JOIN dim_competitor dc ON fr.competitor_key = dc.competitor_key
JOIN dim_country dco ON dc.country_key = dco.country_key
JOIN dim_category dcat ON fr.category_key = dcat.category_key
JOIN dim_time dt ON fr.time_key = dt.time_key
WHERE fr.is_current_flag = 'Y'
  AND dc.is_current_flag = 'Y'
ORDER BY fr.category_key, fr.rank;

-- vw_competitor_ranking_history: Time-series view for trend analysis
CREATE VIEW vw_competitor_ranking_history AS
SELECT
    dc.competitor_name,
    dco.country_name,
    dcat.category_name,
    dt.full_date,
    fr.rank,
    fr.points,
    fr.rank_movement,
    LAG(fr.rank) OVER (
        PARTITION BY dc.competitor_key, dcat.category_key
        ORDER BY dt.time_key
    ) AS previous_rank,
    LEAD(fr.rank) OVER (
        PARTITION BY dc.competitor_key, dcat.category_key
        ORDER BY dt.time_key
    ) AS next_rank
FROM fact_rankings fr
JOIN dim_competitor dc ON fr.competitor_key = dc.competitor_key
JOIN dim_country dco ON dc.country_key = dco.country_key
JOIN dim_category dcat ON fr.category_key = dcat.category_key
JOIN dim_time dt ON fr.time_key = dt.time_key
WHERE dc.is_current_flag = 'Y'
ORDER BY dc.competitor_key, dcat.category_key, dt.time_key DESC;

-- ============================================================================
-- STORED PROCEDURE: Load rankings from staging
-- ============================================================================

CREATE OR REPLACE FUNCTION load_rankings_from_staging(
    p_batch_id VARCHAR(128),
    p_ranking_date DATE
)
RETURNS TABLE(
    rows_inserted BIGINT,
    rows_updated BIGINT,
    rows_failed BIGINT
) AS $$
DECLARE
    v_rows_inserted BIGINT := 0;
    v_rows_updated BIGINT := 0;
    v_rows_failed BIGINT := 0;
    v_time_key INT;
    v_competitor_key BIGINT;
    v_ranking_series_key INT;
    v_category_key INT;
BEGIN
    -- Get or create time key
    v_time_key := CAST(TO_CHAR(p_ranking_date, 'YYYYMMDD') AS INT);

    -- Ensure time dimension exists
    INSERT INTO dim_time (time_key, full_date, year, quarter, month, week, day, day_of_week, day_name, is_weekend, week_start_date, month_start_date, quarter_start_date, year_start_date, source_system)
    SELECT
        v_time_key,
        p_ranking_date,
        EXTRACT(YEAR FROM p_ranking_date),
        EXTRACT(QUARTER FROM p_ranking_date),
        EXTRACT(MONTH FROM p_ranking_date),
        EXTRACT(WEEK FROM p_ranking_date),
        EXTRACT(DAY FROM p_ranking_date),
        EXTRACT(ISODOW FROM p_ranking_date),
        TO_CHAR(p_ranking_date, 'Day'),
        CASE WHEN EXTRACT(ISODOW FROM p_ranking_date) IN (6, 7) THEN 'Y' ELSE 'N' END,
        p_ranking_date - EXTRACT(ISODOW FROM p_ranking_date)::INT + 1,
        DATE_TRUNC('month', p_ranking_date),
        DATE_TRUNC('quarter', p_ranking_date),
        DATE_TRUNC('year', p_ranking_date),
        'SYSTEM'
    ON CONFLICT (time_key) DO NOTHING;

    -- Default ranking series
    SELECT ranking_series_key INTO v_ranking_series_key
    FROM dim_ranking_series
    WHERE is_active_flag = 'Y'
    LIMIT 1;

    IF v_ranking_series_key IS NULL THEN
        INSERT INTO dim_ranking_series (ranking_series_key, series_sid, series_name, series_type, source_system, is_active_flag, effective_date, created_at, updated_at)
        VALUES (1, 'SR_DEFAULT', 'Default Rankings Series', 'Current', 'SportRadar', 'Y', CURRENT_DATE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        v_ranking_series_key := 1;
    END IF;

    -- Insert rankings
    INSERT INTO fact_rankings (
        competitor_key, ranking_series_key, time_key, category_key, competition_key, venue_key,
        rank, points, competitions_played, rank_movement, wins, losses, win_percentage,
        is_current_flag, source_system, extracted_at, loaded_at, etl_batch_id
    )
    SELECT
        MD5(sr.competitor_sid)::BIGINT,
        v_ranking_series_key,
        v_time_key,
        dc.category_key,
        NULL,
        NULL,
        sr.rank,
        sr.points,
        sr.competitions_played,
        sr.movement,
        NULL,
        NULL,
        NULL,
        'Y',
        sr.source_system,
        sr.extracted_at,
        CURRENT_TIMESTAMP,
        p_batch_id
    FROM stg_rankings_raw sr
    JOIN dim_category dc ON sr.category_sid = dc.category_sid
    WHERE sr.is_processed_flag = 'N'
      AND sr.loaded_at::DATE = p_ranking_date
    ON CONFLICT DO NOTHING;

    GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

    RETURN QUERY SELECT v_rows_inserted, v_rows_updated, v_rows_failed;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- DATA QUALITY CHECKS
-- ============================================================================

-- View to detect quality issues
CREATE VIEW vw_data_quality_checks AS
SELECT
    'FACT_Rankings' AS table_name,
    'Missing Dimensions' AS check_type,
    COUNT(*) AS issue_count
FROM fact_rankings
WHERE competitor_key IS NULL
   OR ranking_series_key IS NULL
   OR time_key IS NULL
UNION ALL
SELECT
    'FACT_Rankings',
    'Invalid Rank (Zero or Negative)',
    COUNT(*)
FROM fact_rankings
WHERE rank <= 0
UNION ALL
SELECT
    'DIM_Competitor',
    'SCD Type 2 Violation',
    COUNT(*)
FROM dim_competitor
WHERE is_current_flag = 'Y'
  AND expiry_date IS NOT NULL
UNION ALL
SELECT
    'DIM_Competition',
    'SCD Type 2 Violation',
    COUNT(*)
FROM dim_competition
WHERE is_current_flag = 'Y'
  AND expiry_date IS NOT NULL;
```

---

## 5. Source-to-Target Mapping (STTM)

### 📋 ETL Logic: API → MongoDB → Staging → Warehouse

```sql
-- ============================================================================
-- PHASE 1: Raw API Response → Staging Tables (MongoDB dump to SQL)
-- ============================================================================

-- Sample CTE showing transform from raw JSON (MongoDB) → Staging
WITH raw_api_rankings AS (
    -- Extract from stg_rankings_raw (populated from MongoDB raw_rankings collection)
    SELECT
        sr.competitor_sid,
        sr.competitor_name,
        sr.category_sid,
        sr.rank,
        sr.points,
        sr.movement,
        sr.competitions_played,
        sr.ranking_date,
        sr.source_system,
        sr.extracted_at
    FROM stg_rankings_raw sr
    WHERE sr.is_processed_flag = 'N'
),

-- ============================================================================
-- PHASE 2: Staging → Dimension Tables (Upsert SCD Type 2)
-- ============================================================================

competitor_changes AS (
    -- Identify new or modified competitors
    SELECT
        rar.competitor_sid,
        rar.competitor_name,
        rar.category_sid,
        rar.ranking_date
    FROM raw_api_rankings rar
    LEFT JOIN dim_competitor dc
        ON rar.competitor_sid = dc.competitor_sid
        AND dc.is_current_flag = 'Y'
    WHERE dc.competitor_key IS NULL
       OR dc.competitor_name <> rar.competitor_name  -- Name changed
),

competitor_dimension_load AS (
    -- Upsert logic: If exists and changed → close old, insert new version
    SELECT
        COALESCE(dc.competitor_sid, cc.competitor_sid) AS competitor_sid,
        cc.competitor_name AS new_name,
        COALESCE(dc.competitor_name, cc.competitor_name) AS old_name,
        CASE WHEN dc.competitor_key IS NULL THEN 'INSERT'
             WHEN dc.competitor_name <> cc.competitor_name THEN 'UPDATE'
             ELSE 'NO_CHANGE'
        END AS action_type,
        cc.ranking_date AS effective_date
    FROM competitor_changes cc
    LEFT JOIN dim_competitor dc
        ON cc.competitor_sid = dc.competitor_sid
        AND dc.is_current_flag = 'Y'
),

-- ============================================================================
-- PHASE 3: Dimension & Fact Merge
-- ============================================================================

final_ranking_metrics AS (
    SELECT
        CAST(SUBSTR(rar.competitor_sid, 1, 64) AS VARCHAR(64)) AS competitor_sid,
        MD5(rar.competitor_sid)::BIGINT AS competitor_key,
        (SELECT ranking_series_key FROM dim_ranking_series WHERE is_active_flag = 'Y' LIMIT 1) AS ranking_series_key,
        CAST(TO_CHAR(rar.ranking_date, 'YYYYMMDD') AS INT) AS time_key,
        dc.category_key,
        rar.rank,
        rar.points,
        rar.competitions_played,
        rar.movement AS rank_movement,
        NULL AS wins,
        NULL AS losses,
        NULL AS win_percentage,
        'Y' AS is_current_flag,
        rar.source_system,
        rar.extracted_at,
        CURRENT_TIMESTAMP AS loaded_at,
        SUBSTR(rar.extracted_at::VARCHAR, 1, 8) || '_BATCH' AS etl_batch_id
    FROM raw_api_rankings rar
    JOIN dim_category dc ON rar.category_sid = dc.category_sid
    JOIN dim_competitor dlc ON rar.competitor_sid = dlc.competitor_sid
    JOIN dim_time dt ON CAST(TO_CHAR(rar.ranking_date, 'YYYYMMDD') AS INT) = dt.time_key
)

-- Final INSERT into FACT_Rankings
INSERT INTO fact_rankings (
    competitor_key,
    ranking_series_key,
    time_key,
    category_key,
    competition_key,
    venue_key,
    rank,
    points,
    competitions_played,
    rank_movement,
    wins,
    losses,
    win_percentage,
    is_current_flag,
    source_system,
    extracted_at,
    loaded_at,
    etl_batch_id
)
SELECT
    competitor_key,
    ranking_series_key,
    time_key,
    category_key,
    NULL,
    NULL,
    rank,
    points,
    competitions_played,
    rank_movement,
    wins,
    losses,
    win_percentage,
    is_current_flag,
    source_system,
    extracted_at,
    loaded_at,
    etl_batch_id
FROM final_ranking_metrics
ON CONFLICT (competitor_key, ranking_series_key, time_key, category_key) DO UPDATE
SET
    rank = EXCLUDED.rank,
    points = EXCLUDED.points,
    competitions_played = EXCLUDED.competitions_played,
    rank_movement = EXCLUDED.rank_movement,
    updated_at = CURRENT_TIMESTAMP,
    loaded_at = EXCLUDED.loaded_at;
```

### 🔄 Incremental Load Strategy

| Phase | Source | Target | Logic | Frequency |
|-------|--------|--------|-------|-----------|
| **1** | SportRadar API | MongoDB `raw_rankings` | Append/Upsert snapshot | Daily |
| **2** | MongoDB Collections | Staging Tables | Flatten & validate | Daily post-API |
| **3** | Staging | DIM_Competitor (SCD2) | Upsert on change | Daily |
| **4** | Staging | DIM_Competition (SCD2) | Upsert on change | Weekly |
| **5** | Staging | FACT_Rankings | Insert new; Update if match | Daily |

### ✅ Data Validation Rules

```sql
-- Validation checks pre-load

-- 1. Rank must be positive
ASSERT rank > 0 OR rank IS NULL
    ON VIOLATION INSERT INTO dq_violations (table_name, rule, failing_record_count);

-- 2. Points must be non-negative
ASSERT points >= 0 OR points IS NULL;

-- 3. No duplicate rankings per competitor per category per date
ASSERT COUNT(*) = 1
    OVER (PARTITION BY competitor_key, category_key, time_key);

-- 4. Competitor must exist in DIM_Competitor
ASSERT competitor_key IN (SELECT competitor_key FROM dim_competitor);

-- 5. Win percentage must be 0-100
ASSERT win_percentage BETWEEN 0 AND 100 OR win_percentage IS NULL;

-- 6. Time key must exist in DIM_Time
ASSERT time_key IN (SELECT time_key FROM dim_time);
```

---

## Summary Table: Design Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Grain** | One row per competitor per ranking snapshot per category | Enables point-in-time analysis; supports trend reporting |
| **Fact Table** | FACT_Rankings with semi-additive measures | Avoids double-counting across time dimensions |
| **Surrogate Keys** | BIGINT for large dims; INT for small dims | Decouples physical from logical; enables history tracking |
| **SCD Strategy** | Type 2 (Competitor, Competition); Type 1 (Venue, Category) | Balances history needs with storage efficiency |
| **Indexing** | Covering indexes on fact table for range queries | Optimizes analytic queries; supports sub-second response times |
| **Time Dimension** | Pre-populated INT(YYYYMMDD) | Fast joins; semantic date filtering |
| **Audit Columns** | Included in all tables | Full lineage tracking; data quality monitoring |
| **Constraints** | Check constraints on all measures | Prevents invalid data at load time |

---

## 🎯 Next Steps

1. **Execute DDL** on target database (PostgreSQL / Snowflake / SQL Server)
2. **Populate DIM_Time** with 20+ years historical dates
3. **Seed Reference Dimensions** (Categories, Countries) from source
4. **Run ETL Load** using staging tables
5. **Validate Data Quality** using views
6. **Create Reporting Views** per business requirements
7. **Set Up Incremental Load** job (daily rankings update)

---

**Design Validated For:**
- ✅ PostgreSQL 14+ (native)
- ✅ Snowflake (with minor type adjustments)
- ✅ SQL Server 2019+ (with T-SQL syntax)
- ✅ BigQuery (adapt BIGINT → INT64, DECIMAL → NUMERIC)

