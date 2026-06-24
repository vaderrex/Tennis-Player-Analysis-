# MongoDB ETL Integration Guide

## Overview

This guide explains the integrated **API → MongoDB → ETL** workflow for the Tennis Rankings ETL system.

### Architecture

```
┌─────────────────┐
│  SportRadar API │
│   (Endpoint)    │
└────────┬────────┘
         │ Fetch JSON
         ▼
┌─────────────────────────┐
│  api_requests.py        │ ◄─── stores_api_response_to_mongodb()
│  (API Client)           │
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  MongoDB (tennis_staging)        │
│  Collections:                    │
│  - raw_competitions              │
│  - raw_complexes                 │
│  - raw_rankings                  │
└────────┬─────────────────────────┘
         │ Read from MongoDB
         ▼
┌──────────────────────────────────┐
│  ETL Transforms                  │
│  (tennis_etl/transforms.py)      │
│  - transform_competitions()      │
│  - transform_complexes()         │
│  - transform_rankings()          │
└────────┬─────────────────────────┘
         │ Upsert normalized data
         ▼
┌──────────────────────────────────┐
│  SQL Warehouse                   │
│  (PostgreSQL/MySQL/SQLite)       │
│  Tables:                         │
│  - categories                    │
│  - competitions                  │
│  - complexes                     │
│  - venues                        │
│  - competitors                   │
│  - rankings                      │
└──────────────────────────────────┘
```

## Quick Start

### 1. Setup MongoDB Connection

Ensure your `.env` file has a valid MongoDB URL:

```bash
DATABASE_URL=mongodb://tennis_user:tennis_password@localhost:27017/tennis_rankings
```

### 2. Test API → MongoDB → ETL Flow

Run the integrated test:

```bash
python api_test.py --with-mongodb
```

This will:
- ✅ Fetch data from SportRadar API
- ✅ Store raw JSON in MongoDB (`tennis_staging` database)
- ✅ Retrieve the data back from MongoDB
- ✅ Show ETL entry point

### 3. Run Full ETL Pipeline

After API data is in MongoDB, run the ETL:

```bash
python -m tennis_etl.run_etl
```

This will:
- Read from MongoDB staging collections
- Transform/normalize the data
- Load into SQL warehouse

## Module Reference

### `tennis_etl/mongo_storage.py`

Core MongoDB operations for storing/retrieving API responses.

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `store_competitions()` | Store competitions API response |
| `store_complexes()` | Store complexes API response |
| `store_rankings()` | Store rankings API response |
| `retrieve_api_response()` | Retrieve stored API response by collection |
| `create_mongo_client()` | Create MongoDB connection |

**Example:**

```python
from tennis_etl.mongo_storage import store_competitions, retrieve_api_response

# Store API response
store_competitions(mongo_url, api_response_json)

# Retrieve later
data = retrieve_api_response(mongo_url, "raw_competitions")
```

### `api_requests.py` (Enhanced)

New MongoDB storage integration functions:

| Function | Purpose |
|----------|---------|
| `store_api_response_to_mongodb()` | Store any API response to MongoDB |
| `retrieve_api_response_from_mongodb()` | Retrieve stored API response |

**Example:**

```python
from api_requests import store_api_response_to_mongodb

# Store API response
store_api_response_to_mongodb(
    response_data=api_json,
    collection_type="competitions",
    mongo_url=os.getenv("DATABASE_URL")
)
```

### `api_test.py` (Enhanced)

New test function for integrated workflow:

| Function | Purpose |
|----------|---------|
| `test_api_with_mongodb_storage()` | End-to-end API → MongoDB → ETL test |
| `test_sportradar_api()` | Basic API test (original) |

## Data Flow Details

### Step 1: API → MongoDB Storage

When you call the API and store results:

```python
# Fetch from SportRadar API
response = client.get_competitions()

# Store in MongoDB
store_competitions(mongo_url, response)

# Data structure in MongoDB:
{
    "_id": ObjectId(...),
    "endpoint_id": "competitions",
    "data": { ... actual API response JSON ... },
    "stored_at": ISODate("2024-05-25T10:30:00Z"),
    "source": "api"
}
```

### Step 2: MongoDB → ETL Transforms

The ETL pipeline reads from MongoDB staging:

```python
# In ingestion_pipeline.py
def retrieve_from_mongodb():
    client = MongoClient(mongo_url)
    db = client["tennis_staging"]
    
    # Read raw API responses
    competitions = db["raw_competitions"].find_one(...)
    complexes = db["raw_complexes"].find_one(...)
    rankings = db["raw_rankings"].find_one(...)
    
    # Extract and transform
    return transform_competitions(competitions["data"])
```

### Step 3: ETL → SQL Warehouse

Transforms are loaded into SQL tables:

```python
# Normalized data in SQL
# Before (MongoDB): raw nested JSON
{
    "competitions": [
        {"id": "...", "name": "...", "category": {...}, ...}
    ]
}

# After (SQL): normalized tables
competitions table:
  - id (PK)
  - name
  - category_id (FK)
  - ...

categories table:
  - id (PK)
  - name
  - ...
```

## Configuration

### Environment Variables

```bash
# MongoDB Connection
DATABASE_URL=mongodb://user:pass@host:port/database

# SportRadar API
SPORTRADAR_API_KEY=your_api_key
SPORTRADAR_ACCESS_LEVEL=trial|production
SPORTRADAR_LANGUAGE_CODE=en

# HTTP Settings
HTTP_TIMEOUT_SECONDS=20
HTTP_MAX_RETRIES=4
```

### MongoDB Collections

**Database:** `tennis_staging`

| Collection | Purpose | Data Source |
|-----------|---------|-------------|
| `raw_competitions` | Raw competitions API response | SportRadar API |
| `raw_complexes` | Raw complexes API response | SportRadar API |
| `raw_rankings` | Raw rankings API response | SportRadar API |

## Error Handling

### Missing MongoDB Connection

If MongoDB is unavailable:
- API responses are still fetched ✅
- Storage to MongoDB is skipped ⚠️
- ETL cannot run until data is in MongoDB ❌

**Solution:** Ensure MongoDB is running and `DATABASE_URL` is set.

### Invalid MongoDB URL

Error: `MongoStorageError: Failed to connect to MongoDB`

**Solution:** 
- Check connection string format: `mongodb://user:pass@host:port/db`
- Verify MongoDB is running
- Check firewall/network access

### Missing API Key

Error: `Missing required environment variables: SPORTRADAR_API_KEY`

**Solution:** Add `SPORTRADAR_API_KEY` to `.env` file

## Idempotency

Both API storage and ETL are idempotent:

- **Multiple API calls:** Same data stored in MongoDB (replaces on endpoint_id)
- **Multiple ETL runs:** Same normalized data in SQL (upserts on primary key)

This means:
```bash
# Safe to run multiple times
python api_test.py --with-mongodb
python -m tennis_etl.run_etl

# Data will be consistent, not duplicated
```

## Troubleshooting

### Test Basic API (without MongoDB)
```bash
python api_test.py
```

### Test with MongoDB
```bash
python api_test.py --with-mongodb
```

### Verify MongoDB Data
```bash
# Connect to MongoDB
mongosh mongodb://user:pass@localhost:27017/tennis_staging

# List collections
db.getCollectionNames()

# Check competition data
db.raw_competitions.findOne()
```

### Run ETL Pipeline
```bash
python -m tennis_etl.run_etl
```

## Example: Complete Workflow

```bash
# 1. Setup environment
echo "SPORTRADAR_API_KEY=your_key" >> .env
echo "DATABASE_URL=mongodb://localhost:27017/tennis_rankings" >> .env

# 2. Test API connection
python api_test.py

# 3. Test full pipeline with MongoDB
python api_test.py --with-mongodb

# 4. Verify MongoDB data
mongosh ...
db.raw_competitions.findOne()

# 5. Run ETL pipeline
python -m tennis_etl.run_etl

# 6. Query SQL warehouse
# (depends on your SQL setup)
```

## Next Steps

- ✅ Implement data freshness checks (auto-refresh API data)
- ✅ Add data validation in MongoDB before ETL
- ✅ Implement data versioning in MongoDB
- ✅ Add monitoring/alerting for pipeline failures
- ✅ Create scheduled job to run pipeline (cron/Airflow)

## Support

For issues or questions:
1. Check `.env` configuration
2. Verify MongoDB connection
3. Review logs in console output
4. Check MongoDB collections directly
