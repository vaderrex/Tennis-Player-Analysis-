# Tennis Rankings Explorer - Phase 1 Quick Start

## 5-Minute Setup

### Prerequisites

- Python 3.10+
- PostgreSQL (or MySQL) running locally
- MongoDB running locally (optional, can skip staging)
- SportRadar Tennis API key (get from https://developer.sportradar.com)

### Installation

```powershell
# Clone/navigate to project
cd C:\Users\richa\OneDrive\Desktop\Tennis

# Create virtual environment (optional but recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Configuration

#### Step 1: Create PostgreSQL Database

```powershell
# Connect to PostgreSQL
psql -U postgres

# In psql:
CREATE DATABASE tennis_rankings;
\q
```

#### Step 2: Set Environment Variables

```powershell
$env:SPORTRADAR_API_KEY = "your-api-key-here"
$env:DATABASE_URL = "postgresql+psycopg://postgres:password@localhost/tennis_rankings"
$env:MONGODB_URL = "mongodb://localhost:27017"
```

Or create a `.env` file:
```
SPORTRADAR_API_KEY=your-api-key
DATABASE_URL=postgresql+psycopg://postgres:password@localhost/tennis_rankings
MONGODB_URL=mongodb://localhost:27017
SPORTRADAR_ACCESS_LEVEL=trial
SPORTRADAR_LANGUAGE_CODE=en
HTTP_TIMEOUT_SECONDS=20
HTTP_MAX_RETRIES=4
```

#### Step 3 (Optional): Start MongoDB

If you want full pipeline with MongoDB staging:

```powershell
# Windows with Docker Desktop
docker run -d --name mongo -p 27017:27017 mongo:latest

# Or using MongoDB Community Edition
mongod
```

## Running the Pipeline

### Full Pipeline (API → MongoDB → SQL)

```powershell
python -m tennis_etl.ingestion_pipeline
```

Expected output:
```
============================================================
PHASE 1 INGESTION PIPELINE TEST SUITE
============================================================
[2024-12-21 10:30:45] INFO [PHASE 1A] Fetching raw data from SportRadar Tennis API...
[2024-12-21 10:30:48] INFO [PHASE 1A] API extraction complete
[2024-12-21 10:30:48] INFO [PHASE 1B] Staging raw payloads to MongoDB...
[2024-12-21 10:30:49] INFO [PHASE 1B] MongoDB staging complete
[2024-12-21 10:30:49] INFO [PHASE 1C] Extracting from MongoDB staging...
[2024-12-21 10:30:50] INFO [PHASE 1C] Transforming and flattening...
[2024-12-21 10:30:51] INFO [PHASE 1C] Loading into SQL warehouse...
============================================================
Pipeline success!
```

### Quick Test (No MongoDB Required)

```powershell
$env:SKIP_STAGING = "true"
python -m tennis_etl.ingestion_pipeline
```

### Run Tests

```powershell
python test_ingestion_pipeline.py
```

## Verify the Data

### SQL Queries

```powershell
# Connect to PostgreSQL
psql -U postgres -d tennis_rankings

# In psql:
SELECT COUNT(*) as categories FROM categories;
SELECT COUNT(*) as competitions FROM competitions;
SELECT COUNT(*) as complexes FROM complexes;
SELECT COUNT(*) as venues FROM venues;
SELECT COUNT(*) as competitors FROM competitors;
SELECT COUNT(*) as rankings FROM competitor_rankings;

# See top competitors
SELECT c.name, cr.rank, cr.points 
FROM competitors c 
JOIN competitor_rankings cr ON c.competitor_id = cr.competitor_id 
ORDER BY cr.rank 
LIMIT 10;

\q
```

### MongoDB Queries

```powershell
# Connect to MongoDB
mongosh

# In mongosh:
use tennis_staging
db.raw_competitions.findOne()
db.raw_complexes.findOne()
db.raw_rankings.findOne()
exit
```

## Architecture at a Glance

```
SportRadar API (3 endpoints)
    ↓ (fetch raw JSON)
MongoDB Staging (tennis_staging)
    ↓ (extract, transform)
ETL Transforms (flatten nested structures)
    ↓ (load normalized data)
SQL Warehouse (6 tables, 300+ rows)
    ↓ (Phase 2+: analytical queries)
Streamlit Dashboard (Phase 3+)
```

### Database Schema

**6 Tables**:
1. `categories` - Tour categories (ATP, WTA, ITF)
2. `competitions` - Competition hierarchy
3. `complexes` - Venue complexes
4. `venues` - Venue details (nested in complexes)
5. `competitors` - Competitor/team info
6. `competitor_rankings` - Current ranking snapshot

**Foreign Keys**:
- competitions.category_id → categories.category_id
- competitions.parent_id → competitions.competition_id (self)
- venues.complex_id → complexes.complex_id
- competitor_rankings.competitor_id → competitors.competitor_id

## Troubleshooting

### "Missing environment variables"

```powershell
# Verify env vars are set:
$env:SPORTRADAR_API_KEY
$env:DATABASE_URL
$env:MONGODB_URL

# Or set them:
$env:SPORTRADAR_API_KEY = "your-key"
$env:DATABASE_URL = "postgresql+psycopg://postgres:pass@localhost/tennis_rankings"
```

### "Failed to connect to MongoDB"

Option 1: Start MongoDB
```powershell
docker run -d --name mongo -p 27017:27017 mongo:latest
```

Option 2: Skip MongoDB staging
```powershell
$env:SKIP_STAGING = "true"
python -m tennis_etl.ingestion_pipeline
```

### "Failed to connect to database"

1. Verify PostgreSQL is running
2. Verify database exists: `psql -U postgres -l` (look for tennis_rankings)
3. Check connection string in `$env:DATABASE_URL`
4. Create database if needed: `psql -U postgres -c "CREATE DATABASE tennis_rankings;"`

### "API returned invalid JSON" or Rate Limit Errors

1. Verify API key is correct
2. Check SportRadar API status
3. Wait a few minutes and retry (respects rate limits automatically)
4. Check HTTP_MAX_RETRIES and HTTP_TIMEOUT_SECONDS settings

## Next Steps

1. **Verify Pipeline**: Run `python test_ingestion_pipeline.py`
2. **Phase 2**: Query builder for analytics (20+ queries)
3. **Phase 3**: Streamlit dashboard with custom dark theme
4. **Phase 4**: Interactive views (filters, details, geo map, leaderboards)

See `PHASE_1.md` for detailed architecture documentation.
