# Phase 1 Combined Documentation

> Combined from `PHASE_1.md`, `PHASE_1_API_REFERENCE.md`, and `PHASE_1_IMPLEMENTATION_SUMMARY.md`

---

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
```

---

# Phase 1 Python API Reference

Quick reference for programmatic usage of the ingestion pipeline.

## Imports

```python
from tennis_etl.ingestion_pipeline import (
    run_full_pipeline,           # Main entry point
    stage_to_mongodb,            # Part A: API -> MongoDB
    extract_from_mongodb,        # Part C: MongoDB -> Python
    PipelineCounts,              # Return type
    StagingCounts,               # MongoDB staging counts
    MongoStagingError,           # Exception
)
from tennis_etl.config import Settings
```

## Running the Pipeline

### Full Pipeline

```python
from tennis_etl.config import Settings
from tennis_etl.ingestion_pipeline import run_full_pipeline

# Load settings from environment (SPORTRADAR_API_KEY, DATABASE_URL)
settings = Settings.from_environment()

# Run full pipeline (API -> MongoDB -> SQL)
counts = run_full_pipeline(
    settings=settings,
    mongo_url="mongodb://localhost:27017",
    skip_staging=False,  # Set True to skip MongoDB
)

# Access counts
print(counts.warehouse_categories)      # int
print(counts.warehouse_competitors)     # int
print(counts.warehouse_rankings)        # int
print(str(counts))                      # Full summary
```

### Quick Test (Skip MongoDB)

```python
counts = run_full_pipeline(
    settings=settings,
    skip_staging=True,  # Skip MongoDB for quick iteration
)
```

## API -> MongoDB Staging (Part A)

### Fetch and Stage Data

```python
from tennis_etl.api import SportRadarTennisClient
from tennis_etl.ingestion_pipeline import stage_to_mongodb

# Create API client
client = SportRadarTennisClient(
    api_key="your-api-key",
    timeout_seconds=20,
    max_retries=4,
)

# Fetch raw data
competitions = client.get_competitions()
complexes = client.get_complexes()
rankings = client.get_doubles_competitor_rankings()

# Stage to MongoDB
staging_counts = stage_to_mongodb(
    competitions_payload=competitions,
    complexes_payload=complexes,
    rankings_payload=rankings,
    mongo_url="mongodb://localhost:27017",
)

print(f"Competitions staged: {staging_counts.competitions}")
print(f"Complexes staged: {staging_counts.complexes}")
print(f"Rankings staged: {staging_counts.rankings}")
```

### Error Handling

```python
from tennis_etl.api import SportRadarApiError
from tennis_etl.ingestion_pipeline import MongoStagingError

try:
    counts = stage_to_mongodb(...)
except MongoStagingError as e:
    print(f"MongoDB staging failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## MongoDB -> Python (Part C)

### Extract Data

```python
from tennis_etl.ingestion_pipeline import extract_from_mongodb

# Extract raw payloads from MongoDB
competitions, complexes, rankings = extract_from_mongodb(
    mongo_url="mongodb://localhost:27017"
)

# Access raw data
if competitions:
    print(f"Competitions present: {len(competitions)}")
if complexes:
    print(f"Complexes present: {len(complexes)}")
if rankings:
    print(f"Rankings present: {len(rankings)}")
```

### Error Handling

```python
from tennis_etl.ingestion_pipeline import MongoStagingError

try:
    competitions, complexes, rankings = extract_from_mongodb(
        mongo_url="mongodb://localhost:27017"
    )
except MongoStagingError as e:
    print(f"MongoDB extraction failed: {e}")
```

## Transform (Part C)

### Flatten JSON Structures

```python
from tennis_etl.transforms import (
    transform_competitions,
    transform_complexes,
    transform_doubles_rankings,
)

# Transform API payloads to flat rows
categories, competitions = transform_competitions(competitions_payload)
complexes, venues = transform_complexes(complexes_payload)
competitors, rankings = transform_doubles_rankings(rankings_payload)

# Each returns list of dicts ready for database insertion
print(f"Categories: {len(categories)}")
print(f"Competitions: {len(competitions)}")
print(f"Complexes: {len(complexes)}")
print(f"Venues: {len(venues)}")
print(f"Competitors: {len(competitors)}")
print(f"Rankings: {len(rankings)}")

# Access individual rows
for comp in competitions[:3]:
    print(comp)  # {'competition_id': '...', 'competition_name': '...', ...}
```

## Database Setup (Part B)

### Create Schema

```python
from tennis_etl.database import build_engine, create_schema

# Build engine
engine = build_engine("postgresql+psycopg://user:pass@localhost/tennis_rankings")

# Create tables (idempotent)
create_schema(engine)

# Verify tables exist
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables: {tables}")
```

### Load Data

```python
from tennis_etl.database import build_engine, session_factory
from tennis_etl.loader import load_all

engine = build_engine("postgresql+psycopg://user:pass@localhost/tennis_rankings")
SessionLocal = session_factory(engine)

# Load in foreign-key dependency order
with SessionLocal() as session:
    counts = load_all(
        session=session,
        categories=categories,
        competitions=competitions,
        complexes=complexes,
        venues=venues,
        competitors=competitors,
        rankings=rankings,
    )

print(f"Loaded categories: {counts.categories}")
print(f"Loaded competitions: {counts.competitions}")
print(f"Loaded competitors: {counts.competitors}")
print(f"Loaded rankings: {counts.rankings}")
```

## Query Loaded Data

### With SQLAlchemy ORM

```python
from sqlalchemy import select
from sqlalchemy.orm import Session
from tennis_etl.models import Competitor, CompetitorRanking

with SessionLocal() as session:
    # Query competitors
    competitors = session.execute(
        select(Competitor).limit(10)
    ).scalars().all()
    
    for comp in competitors:
        print(f"{comp.name} ({comp.country})")
    
    # Query rankings with competitor details
    rankings = session.execute(
        select(CompetitorRanking)
        .join(Competitor)
        .order_by(CompetitorRanking.rank)
        .limit(10)
    ).all()
    
    for rank in rankings:
        print(f"#{rank.rank}: {rank.competitor.name} - {rank.points} points")
```

### With Pandas (for Phase 2/3)

```python
import pandas as pd
from sqlalchemy import text

engine = build_engine("postgresql+psycopg://...")

# Query into DataFrame
df = pd.read_sql_query(
    """
    SELECT 
        cr.rank,
        c.name,
        c.country,
        cr.points,
        cr.competitions_played
    FROM competitor_rankings cr
    JOIN competitors c ON cr.competitor_id = c.competitor_id
    ORDER BY cr.rank
    LIMIT 20
    """,
    engine
)

print(df.head(10))
```

## Configuration

### From Environment

```python
from tennis_etl.config import Settings

# Reads from environment variables:
# - SPORTRADAR_API_KEY
# - DATABASE_URL
# - SPORTRADAR_ACCESS_LEVEL (optional, default: 'trial')
# - SPORTRADAR_LANGUAGE_CODE (optional, default: 'en')
# - HTTP_TIMEOUT_SECONDS (optional, default: 20)
# - HTTP_MAX_RETRIES (optional, default: 4)

settings = Settings.from_environment()
print(settings.sportradar_api_key)
print(settings.database_url)
```

### Explicit Configuration

```python
from tennis_etl.config import Settings

settings = Settings(
    sportradar_api_key="your-key",
    database_url="postgresql+psycopg://user:pass@localhost/tennis_rankings",
    access_level="trial",
    language_code="en",
    http_timeout_seconds=20,
    http_max_retries=4,
)
```

## Error Handling Patterns

### API Errors

```python
from tennis_etl.api import (
    SportRadarApiError,
    SportRadarRateLimitError,
    SportRadarTennisClient,
)

client = SportRadarTennisClient(api_key="key")

try:
    data = client.get_competitions()
except SportRadarRateLimitError as e:
    # Rate limit persisted after retries
    print(f"Rate limited: {e}")
    # Wait and retry
except SportRadarApiError as e:
    # API error (invalid JSON, connection failed, etc.)
    print(f"API error: {e}")
    # Handle error
```

### Database Errors

```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from tennis_etl.database import session_factory

SessionLocal = session_factory(engine)

try:
    with SessionLocal() as session:
        counts = load_all(session=session, ...)
except IntegrityError as e:
    # Foreign key or constraint violation
    print(f"Constraint error: {e}")
except SQLAlchemyError as e:
    # Other database error
    print(f"Database error: {e}")
```

### MongoDB Errors

```python
from tennis_etl.ingestion_pipeline import MongoStagingError

try:
    counts = stage_to_mongodb(...)
except MongoStagingError as e:
    # Connection failed, upsert failed, etc.
    print(f"MongoDB error: {e}")
```

## Advanced Usage

### Pipeline with Custom Settings

```python
from tennis_etl.ingestion_pipeline import run_full_pipeline
from tennis_etl.config import Settings

settings = Settings(
    sportradar_api_key="key",
    database_url="mysql+pymysql://user:pass@localhost/tennis",
    access_level="production",
    http_timeout_seconds=30,
    http_max_retries=5,
)

counts = run_full_pipeline(
    settings=settings,
    mongo_url="mongodb://mongo.example.com:27017",
    skip_staging=False,
)
```

### Scheduled Execution

```python
import schedule
import time
from tennis_etl.ingestion_pipeline import run_full_pipeline
from tennis_etl.config import Settings

def run_pipeline():
    settings = Settings.from_environment()
    try:
        counts = run_full_pipeline(settings)
        print(f"Pipeline succeeded: {counts}")
    except Exception as e:
        print(f"Pipeline failed: {e}")
        # Log error, send alert, etc.

# Run every 6 hours
schedule.every(6).hours.do(run_pipeline)
```
