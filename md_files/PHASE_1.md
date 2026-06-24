# Phase 1: API → MongoDB Staging → SQL Warehouse

## Overview

Phase 1 implements a production-grade three-layer ingestion pipeline for Tennis Rankings data:

```
SportRadar API (3 endpoints)
    ↓
MongoDB Staging (tennis_staging database)
    ↓
ETL Transforms (Flatten & Clean)
    ↓
SQL Warehouse (6 normalized tables)
```

## Architecture Components

### Part A: API to MongoDB Staging

**Module**: `tennis_etl/ingestion_pipeline.py` - `stage_to_mongodb()`

Raw API responses are persisted to MongoDB for:
- **Durability**: Survive transient network failures
- **Audit Trail**: Historical record of API snapshots
- **Decoupling**: Separate API fetching from transformations
- **Recovery**: Restart failed ETLs without re-hitting API limits

**Storage Strategy**:
- Database: `tennis_staging`
- Collections:
  - `raw_competitions` - Competitions endpoint snapshot
  - `raw_complexes` - Complexes endpoint snapshot
  - `raw_rankings` - Double competitors rankings endpoint snapshot

**Document Structure**:
```json
{
  "_id": "current_snapshot",
  "endpoint": "competitions|complexes|rankings",
  "payload": { /* full API response */ }
}
```

Using fixed `_id: "current_snapshot"` enables idempotent upserts—reruns overwrite the previous snapshot without accumulating duplicates.

### Part B: Relational SQL Target Setup

**Module**: `tennis_etl/models.py` - SQLAlchemy ORM models

Six normalized tables with proper relationships:

#### Categories (`categories`)
```
PK: category_id (String)
- category_name (String, NOT NULL)
Relationships: 1→M with competitions
```

#### Competitions (`competitions`)
```
PK: competition_id (String)
FK: category_id → categories.category_id
FK: parent_id → competitions.competition_id (self-referential)
- competition_name (String, NOT NULL)
- type (String, nullable)
- gender (String, nullable)
Relationships: M→1 with categories, self-referential parent-child
```

#### Complexes (`complexes`)
```
PK: complex_id (String)
- complex_name (String, NOT NULL)
Relationships: 1→M with venues
```

#### Venues (`venues`)
```
PK: venue_id (String)
FK: complex_id → complexes.complex_id
- venue_name (String, NOT NULL)
- city_name (String, nullable)
- country_name (String, nullable)
- country_code (String, nullable)
- timezone (String, nullable)
Relationships: M→1 with complexes
```

#### Competitors (`competitors`)
```
PK: competitor_id (String)
- name (String, NOT NULL)
- country (String, nullable)
- country_code (String, nullable)
- abbreviation (String, nullable)
Relationships: 1→1 with competitor_rankings (optional)
```

#### Competitor Rankings (`competitor_rankings`)
```
PK: rank_id (Integer, auto-increment)
FK: competitor_id → competitors.competitor_id (UNIQUE constraint)
- rank (Integer, NOT NULL)
- movement (Integer, nullable)
- points (Integer, nullable)
- competitions_played (Integer, nullable)
Relationships: 1→1 with competitors
```

**Key Design Decisions**:
- SportRadar IDs as primary keys enable idempotent upserts
- Rank table uses auto-increment `rank_id` PK + unique constraint on `competitor_id`
- Current snapshot only—no historical ranking timeline in Phase 1

### Part C: MongoDB to SQL Transform & Load

**Modules**:
- `tennis_etl/transforms.py` - Flatten nested structures to DataFrames
- `tennis_etl/loader.py` - Upsert rows in foreign-key dependency order
- `tennis_etl/database.py` - Dialect-aware upsert helpers

#### Transform Pipeline

**1. Competitions Transform** (`transform_competitions()`)
```python
Input: MongoDB payload from raw_competitions
  ├─ Extract category from each competition
  ├─ Extract competition hierarchy
  └─ Return: (categories[], competitions[])

Output:
  - categories: [{"category_id": "...", "category_name": "..."}, ...]
  - competitions: [{"competition_id": "...", "category_id": "...", ...}, ...]
```

**2. Complexes Transform** (`transform_complexes()`)
```python
Input: MongoDB payload from raw_complexes
  ├─ Iterate complexes array
  │  └─ Flatten nested venues array
  └─ Return: (complexes[], venues[])

Output:
  - complexes: [{"complex_id": "...", "complex_name": "..."}, ...]
  - venues: [{"venue_id": "...", "complex_id": "...", ...}, ...]
```

**3. Rankings Transform** (`transform_doubles_rankings()`)
```python
Input: MongoDB payload from raw_rankings
  ├─ Iterate ranking groups (ATP, WTA rankings)
  │  └─ Iterate competitor_rankings array per group
  │     ├─ Extract competitor object
  │     └─ Extract ranking metrics
  └─ Return: (competitors[], rankings[])

Output:
  - competitors: [{"competitor_id": "...", "name": "...", ...}, ...]
  - rankings: [{"competitor_id": "...", "rank": 1, "points": 1000, ...}, ...]
```

#### Load Pipeline

Foreign-key dependency order enforced by `load_all()`:

1. **Categories** ← No dependencies
2. **Competitions** ← Depends on categories
3. **Complexes** ← No dependencies
4. **Venues** ← Depends on complexes
5. **Competitors** ← No dependencies
6. **Rankings** ← Depends on competitors

Each load operation is an **upsert** using dialect-specific SQL:

**PostgreSQL**:
```sql
INSERT INTO table VALUES (...)
ON CONFLICT (conflict_columns) DO UPDATE
SET col1 = EXCLUDED.col1, col2 = EXCLUDED.col2, ...
```

**MySQL**:
```sql
INSERT INTO table VALUES (...)
ON DUPLICATE KEY UPDATE col1 = VALUES(col1), col2 = VALUES(col2), ...
```

**Other** (fallback):
```python
# Lookup by conflict_columns, insert or update
```

## Usage

### Full Pipeline (API → MongoDB → SQL)

```powershell
# Set environment variables
$env:SPORTRADAR_API_KEY = "your-key"
$env:DATABASE_URL = "postgresql+psycopg://user:pass@localhost/tennis_rankings"
$env:MONGODB_URL = "mongodb://localhost:27017"

# Run full pipeline
python -m tennis_etl.ingestion_pipeline
```

**Output**:
```
[2024-12-21 10:30:45] INFO [PHASE 1A] Fetching raw data from SportRadar Tennis API...
[2024-12-21 10:30:48] INFO [PHASE 1A] API extraction complete
[2024-12-21 10:30:48] INFO [PHASE 1B] Staging raw payloads to MongoDB...
[2024-12-21 10:30:49] INFO [PHASE 1B] MongoDB staging complete: competitions=1, complexes=1, rankings=1
[2024-12-21 10:30:49] INFO [PHASE 1C] Extracting from MongoDB staging...
[2024-12-21 10:30:49] INFO [PHASE 1C] MongoDB extraction complete
[2024-12-21 10:30:49] INFO [PHASE 1C] Transforming and flattening nested structures...
[2024-12-21 10:30:49] INFO [PHASE 1C] Transform complete: categories=3, competitions=45, complexes=180, venues=320, competitors=240, rankings=240
[2024-12-21 10:30:49] INFO [PHASE 1C] Initializing SQL warehouse schema...
[2024-12-21 10:30:50] INFO [PHASE 1C] SQL schema ready
[2024-12-21 10:30:50] INFO [PHASE 1C] Loading transformed rows into SQL warehouse...
[2024-12-21 10:30:51] INFO [PHASE 1C] SQL load complete: LoadCounts(categories=3, competitions=45, complexes=180, venues=320, competitors=240, rankings=240)
============================================================
Pipeline success: PipelineCounts(
  staging=StagingCounts(competitions=1, complexes=1, rankings=1),
  warehouse_categories=3, warehouse_competitions=45, warehouse_complexes=180,
  warehouse_venues=320, warehouse_competitors=240, warehouse_rankings=240
)
============================================================
```

### Quick Test (Skip MongoDB)

```powershell
$env:SKIP_STAGING = "true"
python -m tennis_etl.ingestion_pipeline
```

Bypasses MongoDB staging for rapid iteration during development.

### Schema Only (Create Tables)

```powershell
python -m tennis_etl.create_schema
```

### Direct API → SQL (Legacy Mode)

```powershell
python -m tennis_etl.run_etl
```

## Error Handling

### Robust Retry Logic

**API Client** (`api.py`):
- Retries on 5xx errors with exponential backoff (2^n seconds, max 60s)
- Respects `Retry-After` header for rate limits (429)
- Raises `SportRadarRateLimitError` after exhausting retries
- Validates JSON payload structure before returning

**MongoDB** (`ingestion_pipeline.py`):
- Validates connection before staging
- Raises `MongoStagingError` on connection/upsert failures
- Gracefully closes client in finally block
- Handles missing collections (returns empty dict for ETL to handle)

**SQL** (`database.py`):
- Catches `IntegrityError` for FK/constraint violations
- Rolls back transactions on errors
- Logs constraint failures for debugging
- Fallback merge strategy for non-PostgreSQL/MySQL dialects

### Transaction Management

- Each table load is independent (no cross-table transactions)
- ETL fails fast on first constraint error
- Failed loads leave database unchanged (rollback)
- Idempotent upserts allow safe retries

## Operational Considerations

### Staging Retention

MongoDB staging is **not purged** after successful loads:
- Previous snapshots accessible for debugging
- To clear staging: `mongodb# use tennis_staging; db.raw_*.deleteMany({})`

### API Rate Limits

SportRadar trial tier typically allows ~50 requests/minute:
- Three endpoints = 3 requests per run
- Safe to run every few minutes during development
- Production: Consider caching or scheduled runs

### Idempotency

Both MongoDB and SQL upserts are idempotent:
- Rerun same pipeline multiple times safely
- New API data overwrites previous versions
- Supports automated retry policies

### Monitoring

Check ingestion status:
```powershell
# SQL row counts
psql -U tennis_user -d tennis_rankings -c "
  SELECT 'categories' as table_name, count(*) as row_count FROM categories
  UNION ALL
  SELECT 'competitions', count(*) FROM competitions
  UNION ALL
  SELECT 'complexes', count(*) FROM complexes
  UNION ALL
  SELECT 'venues', count(*) FROM venues
  UNION ALL
  SELECT 'competitors', count(*) FROM competitors
  UNION ALL
  SELECT 'rankings', count(*) FROM rankings;
"

# MongoDB document presence
mongosh tennis_staging
> db.raw_competitions.findOne()
> db.raw_complexes.findOne()
> db.raw_rankings.findOne()
```

## Dependencies

- `requests` - HTTP client for SportRadar API
- `pymongo` - MongoDB driver
- `sqlalchemy` - ORM and database abstraction
- `pandas` - Data manipulation (future phases)
- `psycopg` - PostgreSQL adapter (optional)
- `pymysql` - MySQL adapter (optional)

## File Structure

```
tennis_etl/
├── ingestion_pipeline.py      # Main orchestration (Part A-C)
├── api.py                     # SportRadar API client
├── config.py                  # Settings from environment
├── models.py                  # SQLAlchemy ORM (Part B)
├── database.py                # Connection and upsert helpers
├── transforms.py              # Flatten transforms (Part C)
├── loader.py                  # Load operations (Part C)
├── create_schema.py           # Schema creation only
└── run_etl.py                 # Legacy direct API→SQL

sql/
├── postgresql_schema.sql      # Raw DDL (PostgreSQL)
└── mysql_schema.sql           # Raw DDL (MySQL)

.env.example                   # Environment template
```

## Next Steps (Phase 2+)

- **Phase 2**: Analytical query functions (`queries.py`)
- **Phase 3**: Streamlit dashboard homepage and custom CSS
- **Phase 4**: Interactive views (filters, details, choropleth, leaderboards)
