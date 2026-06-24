# 🚀 Complete Tennis ETL Setup Guide - SSMS 22 Integration

## Overview

This guide walks you through setting up a complete ETL pipeline that:
1. Fetches data from SportRadar Tennis API
2. Stores raw JSON in MongoDB (staging layer)
3. Processes data with ETL transforms
4. Loads normalized data into SQL Server database (data warehouse)

## Architecture

```
┌──────────────────────┐
│  SportRadar API      │
│  (Tennis Data)       │
└──────────┬───────────┘
           │ fetch JSON
           ▼
┌──────────────────────────────────┐
│ MongoDB (tennis_staging)         │
│ - raw_competitions               │
│ - raw_complexes                  │
│ - raw_rankings                   │
└──────────┬───────────────────────┘
           │ ETL transforms
           │ (normalize, flatten)
           ▼
┌──────────────────────────────────┐
│ SQL Server (TennisRankings)      │
│ Data Warehouse                   │
│ - Categories                     │
│ - Competitions                   │
│ - Complexes                      │
│ - Venues                         │
│ - Competitors                    │
│ - Rankings                       │
│ - Staging_*                      │
│ - ETL_ExecutionLog               │
└──────────────────────────────────┘
```

## Prerequisites

Before starting, ensure you have installed:

- ✅ Python 3.9+ 
- ✅ SQL Server 2022 (or 2019+)
- ✅ SQL Server Management Studio (SSMS) 22
- ✅ MongoDB (local or remote)
- ✅ Visual Studio Code (optional but recommended)

## Step 1: Verify Your Setup

### Check Python Environment

```bash
# Verify Python is installed
python --version

# Create virtual environment (if not already done)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Add missing packages for SQL Server
pip install pyodbc
```

### Check MongoDB

```powershell
# Start MongoDB service
Start-Service MongoDB

# Or if installed via WSL/Docker
docker start mongodb

# Test MongoDB connection
mongosh mongodb://localhost:27017
```

### Check SQL Server

```powershell
# Verify SQL Server is running
Get-Service MSSQLSERVER

# If not running, start it
Start-Service MSSQLSERVER

# Open SSMS and verify you can connect to local server
```

## Step 2: Setup SQL Server Database

### In SQL Server Management Studio (SSMS):

1. **Open SSMS 22**
   - Launch SQL Server Management Studio
   - Connect to your local server (or server name)
   - Choose "Windows Authentication" (recommended)

2. **Create Database**
   - File → Open → File
   - Navigate to: `c:\Users\richa\OneDrive\Desktop\Tennis\sql\create_tennis_warehouse.sql`
   - Click "Execute" (F5)
   - Wait for completion message: ✅ "Database Setup Complete!"

3. **Verify Tables**
   - In Object Explorer, expand "Databases"
   - Expand "TennisRankings"
   - Expand "Tables"
   - You should see all 10 tables created

### Visual Verification

```sql
-- Run in SSMS to verify
USE [TennisRankings];
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'BASE TABLE' 
ORDER BY TABLE_NAME;
```

Expected output:
```
Categories
Competitors
Complexes
Competitions
ETL_ExecutionLog
Rankings
Staging_Competitions
Staging_Complexes
Staging_Rankings
Venues
```

## Step 3: Configure Environment Variables

### Update `.env` File

Edit `c:\Users\richa\OneDrive\Desktop\Tennis\.env`:

```env
# SportRadar API Configuration
SPORTRADAR_API_KEY=9fCYlgsmfouRKae92vrItHKtgSfb4n2KPDzwk4Aa
SPORTRADAR_ACCESS_LEVEL=trial
SPORTRADAR_LANGUAGE_CODE=en

# MongoDB (for staging raw API data)
MONGODB_URL=mongodb://localhost:27017

# SQL Server (for data warehouse) - Use ONE of these:

# Option 1: Windows Authentication (RECOMMENDED - easiest)
DATABASE_URL=mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server

# Option 2: SQL Server Authentication (if using sa account)
# DATABASE_URL=mssql+pyodbc://sa:YourPassword123@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server

# Option 3: Named instance
# DATABASE_URL=mssql+pyodbc://@SERVER_NAME\SQLEXPRESS/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server

# HTTP/API Settings
HTTP_TIMEOUT_SECONDS=20
HTTP_MAX_RETRIES=4
```

## Step 4: Test Connections

### Test MongoDB Connection

```bash
python diagnose_mongodb.py
```

Expected output:
```
✅ Successfully connected to MongoDB
✅ Found database: tennis_staging
```

### Test SQL Server Connection

```bash
python test_sqlserver.py
```

Expected output:
```
✅ Connected to SQL Server
✅ Version: Microsoft SQL Server 2022
✅ Found 10 table(s)
✅ All expected tables found!
```

## Step 5: Run the ETL Pipeline

### Step 5a: Fetch API Data

```bash
# Fetch from SportRadar API and store in MongoDB
python api_test.py --with-mongodb
```

Expected output:
```
🚀 Running with MongoDB storage and ETL pipeline integration...
📡 Step 1: Fetching from API endpoint: ...
✅ API Response received: 123456 bytes
💾 Step 2: Storing in MongoDB
✅ Data stored in MongoDB
🔍 Step 3: Retrieving from MongoDB
✅ Successfully retrieved from MongoDB
✅ Pipeline Test Complete!
```

### Step 5b: Verify Data in MongoDB

```bash
python diagnose_mongodb.py
```

You should see:
```
✅ raw_competitions: X documents
✅ raw_complexes: Y documents
✅ raw_rankings: Z documents
```

### Step 5c: Run ETL Transforms and Load to SQL Server

```bash
# Transform MongoDB data and load into SQL Server
python -m tennis_etl.run_etl
```

Expected output:
```
✅ ETL Pipeline Started
✅ Retrieved competitions from MongoDB
✅ Transformed competitions data
✅ Loaded X records into Categories
✅ Loaded Y records into Competitions
...
✅ ETL Pipeline Completed Successfully!
```

### Step 5d: Verify Data in SQL Server

```bash
python test_sqlserver.py
```

Now you should see row counts > 0 for all tables:
```
✅ Categories: 10 rows
✅ Competitions: 50 rows
✅ Complexes: 15 rows
✅ Venues: 100 rows
✅ Competitors: 500 rows
✅ Rankings: 2000 rows
```

## Step 6: Query Data in SSMS

### View All Competitors

```sql
USE [TennisRankings];
SELECT TOP 10 * FROM [dbo].[Competitors];
```

### View Latest Rankings

```sql
SELECT TOP 20 
    c.FullName,
    cat.CategoryName,
    r.Rank,
    r.Points,
    r.RankingDate
FROM [dbo].[Rankings] r
JOIN [dbo].[Competitors] c ON r.CompetitorID = c.CompetitorID
JOIN [dbo].[Categories] cat ON r.CategoryID = cat.CategoryID
ORDER BY r.RankingDate DESC, r.Rank;
```

### View ETL Pipeline Execution Log

```sql
SELECT * FROM [dbo].[ETL_ExecutionLog]
ORDER BY [StartTime] DESC;
```

### Check Row Counts Summary

```sql
SELECT 
    'Categories' as [Table], COUNT(*) as [Rows]
FROM [dbo].[Categories]
UNION ALL SELECT 'Competitions', COUNT(*) FROM [dbo].[Competitions]
UNION ALL SELECT 'Complexes', COUNT(*) FROM [dbo].[Complexes]
UNION ALL SELECT 'Venues', COUNT(*) FROM [dbo].[Venues]
UNION ALL SELECT 'Competitors', COUNT(*) FROM [dbo].[Competitors]
UNION ALL SELECT 'Rankings', COUNT(*) FROM [dbo].[Rankings]
ORDER BY [Table];
```

## Step 7: Schedule Regular Updates (Optional)

### Create Windows Task Scheduler Job

```powershell
# Run ETL pipeline daily at 2 AM
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument "c:\Users\richa\OneDrive\Desktop\Tennis\-m tennis_etl.run_etl"
$trigger = New-ScheduledTaskTrigger -Daily -At 2AM
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "TennisETL_Daily" `
    -Description "Run Tennis ETL Pipeline Daily"
```

### Create Python Script for Automation

Create `run_full_pipeline.py`:

```python
#!/usr/bin/env python
"""Run complete ETL pipeline: API → MongoDB → SQL Server"""

from dotenv import load_dotenv
import subprocess
import sys

load_dotenv()

print("🚀 Starting Full ETL Pipeline...")

# Step 1: Fetch API data
print("\n📡 Step 1: Fetching API data...")
result = subprocess.run([sys.executable, "api_test.py", "--with-mongodb"])
if result.returncode != 0:
    print("❌ API fetch failed!")
    sys.exit(1)

# Step 2: Run ETL
print("\n🔄 Step 2: Running ETL transforms...")
result = subprocess.run([sys.executable, "-m", "tennis_etl.run_etl"])
if result.returncode != 0:
    print("❌ ETL failed!")
    sys.exit(1)

print("\n✅ Full Pipeline Completed Successfully!")
```

Then run with:
```bash
python run_full_pipeline.py
```

## Troubleshooting

### "Cannot connect to SQL Server"

```powershell
# Check if SQL Server is running
Get-Service MSSQLSERVER

# Start SQL Server if stopped
Start-Service MSSQLSERVER

# Verify it's listening on port 1433
netstat -ano | findstr :1433
```

### "Database does not exist"

```sql
-- In SSMS, run the create_tennis_warehouse.sql script again
USE master;
DROP DATABASE [TennisRankings]; -- Optional: only if needed
-- Then re-run create_tennis_warehouse.sql
```

### "ODBC Driver not found"

```powershell
# Download from Microsoft
# https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

# Or install via chocolatey
choco install sql-server-odbcdriver
```

### "Authentication failed"

Try different connection string options:

```env
# Windows Auth (no credentials needed)
DATABASE_URL=mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server

# With explicit server name
DATABASE_URL=mssql+pyodbc://@DESKTOP-ABC123/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server

# SQL Server Auth
DATABASE_URL=mssql+pyodbc://sa:Password123@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

## Command Reference

| Command | Purpose |
|---------|---------|
| `python api_test.py` | Test API connection (basic) |
| `python api_test.py --with-mongodb` | Fetch API + store in MongoDB |
| `python diagnose_mongodb.py` | Check MongoDB connection & data |
| `python test_sqlserver.py` | Check SQL Server connection & tables |
| `python -m tennis_etl.run_etl` | Run full ETL pipeline |
| `python run_full_pipeline.py` | Run both API fetch and ETL |

## File Structure

```
Tennis/
├── .env                              # Environment config
├── requirements.txt                  # Python dependencies
├── api_test.py                       # API test script
├── diagnose_mongodb.py               # MongoDB diagnostic
├── test_sqlserver.py                 # SQL Server diagnostic
├── SQL_SERVER_SETUP.md               # Detailed SQL Server setup
├── MONGODB_ETL_GUIDE.md              # MongoDB integration guide
├── sql/
│   ├── create_tennis_warehouse.sql   # SQL Server database creation
│   ├── postgresql_schema.sql         # PostgreSQL alternative
│   └── mysql_schema.sql              # MySQL alternative
└── tennis_etl/
    ├── run_etl.py                    # Main ETL runner
    ├── api.py                        # SportRadar API client
    ├── database.py                   # Database helpers (SQL Server support)
    ├── models.py                     # SQLAlchemy ORM models
    ├── transforms.py                 # Data transformation logic
    ├── loader.py                     # Data loading to SQL Server
    ├── mongo_storage.py              # MongoDB storage helpers
    └── config.py                     # Configuration management
```

## Next Steps

- ✅ Verify all components are working
- ✅ Run ETL pipeline once to populate data
- ✅ Query data in SSMS to confirm
- ✅ Set up automated scheduling (optional)
- ✅ Monitor ETL_ExecutionLog table for performance

## Support & Resources

- **SQL Server Docs**: https://docs.microsoft.com/en-us/sql/
- **MongoDB Docs**: https://docs.mongodb.com/
- **SportRadar API**: Check your API documentation
- **SQLAlchemy**: https://docs.sqlalchemy.org/

## Summary

You now have a complete data pipeline:
1. **API Layer**: SportRadar Tennis API
2. **Staging Layer**: MongoDB for raw data storage
3. **Processing Layer**: Python ETL with transformations
4. **Warehouse Layer**: SQL Server for analytics and reporting

All components are production-ready and can be monitored via the ETL_ExecutionLog table in SQL Server.
