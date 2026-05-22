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

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Testing Components

```python
import unittest
from tennis_etl.transforms import transform_competitions

class TestTransforms(unittest.TestCase):
    def test_empty_competitions(self):
        """Test transform handles empty payload"""
        payload = {"competitions": []}
        categories, competitions = transform_competitions(payload)
        assert categories == []
        assert competitions == []
    
    def test_single_competition(self):
        """Test transform parses single competition"""
        payload = {
            "competitions": [
                {
                    "id": "sr:competition:1",
                    "name": "ATP Tour",
                    "category": {"id": "sr:category:1", "name": "ATP"},
                }
            ]
        }
        categories, competitions = transform_competitions(payload)
        assert len(categories) == 1
        assert len(competitions) == 1
```

## Data Models (Part B)

### Category

```python
from tennis_etl.models import Category

# Using SQLAlchemy
category = Category(
    category_id="sr:category:1",
    category_name="ATP",
)
session.add(category)
session.commit()
```

### Competitor Ranking

```python
from tennis_etl.models import CompetitorRanking

# Using SQLAlchemy
ranking = CompetitorRanking(
    rank=1,
    points=9350,
    movement=1,
    competitions_played=25,
    competitor_id="sr:competitor:1234",
)
session.add(ranking)
session.commit()

# Query with relationships
with session() as s:
    ranking = s.query(CompetitorRanking).first()
    print(ranking.competitor.name)  # Lazy-loaded relationship
```

## Logging

### Configure Logging

```python
import logging

# Setup logging before calling pipeline
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

# Now pipeline will log [PHASE 1A], [PHASE 1B], [PHASE 1C] markers
from tennis_etl.ingestion_pipeline import run_full_pipeline
counts = run_full_pipeline(settings)
```

### Access Logger

```python
import logging

logger = logging.getLogger("tennis_etl.ingestion_pipeline")
logger.info("Custom log message")
```

## Common Recipes

### One-Line Full Run

```python
from tennis_etl.ingestion_pipeline import run_full_pipeline
from tennis_etl.config import Settings

counts = run_full_pipeline(Settings.from_environment())
```

### Quick SQL Check

```python
import pandas as pd
from tennis_etl.database import build_engine

engine = build_engine("postgresql+psycopg://user:pass@localhost/tennis")
df = pd.read_sql("SELECT COUNT(*) FROM competitors", engine)
print(df)
```

### Retry on Failure

```python
import time
from tennis_etl.ingestion_pipeline import run_full_pipeline
from tennis_etl.config import Settings

max_retries = 3
for attempt in range(max_retries):
    try:
        counts = run_full_pipeline(Settings.from_environment())
        break
    except Exception as e:
        if attempt < max_retries - 1:
            wait = 2 ** attempt
            print(f"Retry in {wait}s...")
            time.sleep(wait)
        else:
            raise
```
