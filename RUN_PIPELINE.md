# Running the Phase 1 Ingestion Pipeline

## One-Liner Quick Start

```powershell
# Set env vars and run full pipeline
$env:SPORTRADAR_API_KEY = "your-key"; $env:DATABASE_URL = "postgresql+psycopg://user:pass@localhost/tennis_rankings"; $env:MONGODB_URL = "mongodb://localhost:27017"; python -m tennis_etl.ingestion_pipeline
```

## Step-by-Step

### 1. Environment Setup

```powershell
# Option A: Use .env file (create from .env.example)
# Edit .env with your values:
# SPORTRADAR_API_KEY=your-key
# DATABASE_URL=postgresql+psycopg://user:pass@localhost/tennis_rankings
# MONGODB_URL=mongodb://localhost:27017

# Option B: Set individual env vars
$env:SPORTRADAR_API_KEY = "your-api-key"
$env:DATABASE_URL = "postgresql+psycopg://postgres:password@localhost/tennis_rankings"
$env:MONGODB_URL = "mongodb://localhost:27017"
$env:SPORTRADAR_ACCESS_LEVEL = "trial"
$env:SPORTRADAR_LANGUAGE_CODE = "en"
$env:HTTP_TIMEOUT_SECONDS = "20"
$env:HTTP_MAX_RETRIES = "4"
```

### 2. Database Setup

```powershell
# PostgreSQL
psql -U postgres -c "CREATE DATABASE tennis_rankings;"

# Or MySQL
mysql -u root -p -e "CREATE DATABASE tennis_rankings;"
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Run Pipeline

#### Full Pipeline (API → MongoDB → SQL)
```powershell
python -m tennis_etl.ingestion_pipeline
```

#### Quick Test (API → SQL, Skip MongoDB)
```powershell
$env:SKIP_STAGING = "true"
python -m tennis_etl.ingestion_pipeline
```

#### Schema Only (Create Tables)
```powershell
python -m tennis_etl.create_schema
```

#### Direct API→SQL (Legacy Mode)
```powershell
python -m tennis_etl.run_etl
```

#### Run Tests
```powershell
python test_ingestion_pipeline.py
```

## Expected Output

### Success
```
============================================================
Pipeline complete: Staging staged: competitions=1, complexes=1, rankings=1; 
warehouse_total=1168 (categories=3, competitions=45, complexes=180, venues=320, 
competitors=240, rankings=240)
============================================================
```

### Failed MongoDB Connection (Acceptable with skip_staging)
```
✗ MongoDB connection failed: mongodb://localhost:27017
  Ensure MongoDB is running (e.g., 'mongod' or Docker container)
```

### Missing Environment Variable
```
ValueError: Missing required environment variables: SPORTRADAR_API_KEY, DATABASE_URL
```

## Verification

### Check SQL Data
```powershell
# Connect to database
psql -U postgres -d tennis_rankings

# In psql:
SELECT 'categories' as table_name, count(*) FROM categories
UNION ALL SELECT 'competitions', count(*) FROM competitions
UNION ALL SELECT 'complexes', count(*) FROM complexes
UNION ALL SELECT 'venues', count(*) FROM venues
UNION ALL SELECT 'competitors', count(*) FROM competitors
UNION ALL SELECT 'rankings', count(*) FROM competitor_rankings;

# See top competitors
SELECT c.name, cr.rank, cr.points FROM competitors c 
JOIN competitor_rankings cr ON c.competitor_id = cr.competitor_id 
ORDER BY cr.rank LIMIT 10;
```

### Check MongoDB Data
```powershell
mongosh
use tennis_staging
db.raw_competitions.countDocuments()
db.raw_complexes.countDocuments()
db.raw_rankings.countDocuments()
```

## Environment Variables Reference

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `SPORTRADAR_API_KEY` | Yes | `abc123def456` | Get from https://developer.sportradar.com |
| `DATABASE_URL` | Yes | `postgresql+psycopg://user:pass@localhost/tennis_rankings` | PostgreSQL or MySQL |
| `MONGODB_URL` | No | `mongodb://localhost:27017` | Required only if not skipping staging |
| `SPORTRADAR_ACCESS_LEVEL` | No | `trial` | trial or production |
| `SPORTRADAR_LANGUAGE_CODE` | No | `en` | Language code for API |
| `HTTP_TIMEOUT_SECONDS` | No | `20` | Request timeout in seconds |
| `HTTP_MAX_RETRIES` | No | `4` | Max retries on transient failures |
| `SKIP_STAGING` | No | `true` | Skip MongoDB staging for quick test |

## Troubleshooting

### "ModuleNotFoundError: No module named 'pymongo'"
```powershell
pip install pymongo
```

### "Unable to connect to database"
```powershell
# Verify database exists
psql -U postgres -l | grep tennis

# Or create it
psql -U postgres -c "CREATE DATABASE tennis_rankings;"
```

### "MongoDB connection refused"
```powershell
# Start MongoDB
docker run -d --name mongo -p 27017:27017 mongo:latest

# Or use skip_staging for quick test
$env:SKIP_STAGING = "true"
```

### "SportRadar rate limit exceeded"
- Wait 60+ seconds (pipeline respects Retry-After header)
- Check your API tier (trial has ~50 requests/minute)
- Consider scheduling runs during off-peak hours

## Execution Modes

| Mode | Command | Use Case | Duration |
|------|---------|----------|----------|
| Full | `python -m tennis_etl.ingestion_pipeline` | Production, audit trail | 8-10s |
| Skip MongoDB | `SKIP_STAGING=true python -m ...` | Development iteration | 6-8s |
| Schema Only | `python -m tennis_etl.create_schema` | Table creation | <1s |
| Direct ETL | `python -m tennis_etl.run_etl` | Legacy/testing | 7-9s |
| Test Suite | `python test_ingestion_pipeline.py` | Validation | 5-15s |

## Docker Quick Start

If you have Docker Desktop:

```powershell
# Start MongoDB
docker run -d --name mongo -p 27017:27017 mongo:latest

# Start PostgreSQL
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:latest

# Create database
docker exec postgres psql -U postgres -c "CREATE DATABASE tennis_rankings;"

# Run pipeline
python -m tennis_etl.ingestion_pipeline
```

## Integration with Phase 2+

Once Phase 1 completes successfully:

**Phase 2 (Query Functions)**
```python
from tennis_etl.queries import highest_points_current_week
df = highest_points_current_week()  # Returns DataFrame
```

**Phase 3 (Streamlit Dashboard)**
```powershell
streamlit run streamlit_app.py
```
