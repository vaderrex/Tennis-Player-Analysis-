# SQL Server Database Setup Guide for SSMS 22

## Overview

This guide walks you through setting up a SQL Server database to store Tennis ETL output.

## Prerequisites

- SQL Server 2022 (or 2019+) installed
- SQL Server Management Studio (SSMS) installed
- Python with `pyodbc` package installed
- Windows Authentication or SQL Server login credentials

## Step 1: Create Database in SSMS

### Option A: Using SQL Script (Recommended)

1. **Open SSMS 22**
   - Launch SQL Server Management Studio

2. **Connect to Your SQL Server**
   - Server name: `DESKTOP-XXXXX` or `localhost`
   - Authentication: Windows Authentication (or SQL Server Auth)
   - Click **Connect**

3. **Open the SQL Script**
   - File → Open → File
   - Navigate to: `c:\Users\richa\OneDrive\Desktop\Tennis\sql\create_tennis_warehouse.sql`
   - Click **Open**

4. **Execute the Script**
   - Click **Execute** (F5)
   - Wait for completion messages
   - Verify success: ✅ all tables created

5. **Verify Database Created**
   - In Object Explorer, refresh (F5)
   - Expand "Databases"
   - You should see **TennisRankings** database
   - Expand it to see all tables (Categories, Competitions, Complexes, Venues, Competitors, Rankings, etc.)

### Option B: Using T-SQL Directly

1. New Query (Ctrl+N)
2. Paste the script content
3. Execute (F5)

## Step 2: Find Your SQL Server Connection Details

In SSMS:
1. Right-click your Server name → **Properties**
2. Note the following:
   - **Server name**: (e.g., `DESKTOP-ABC123` or `SQL-SERVER-01`)
   - **Database**: Select `TennisRankings`
   - **Authentication**: Windows or SQL Server

### Find ODBC Driver

```powershell
# In PowerShell
Get-OdbcDriver -Platform 64-bit | Where-Object {$_.Name -match "SQL"}
```

Expected output:
```
Name: ODBC Driver 17 for SQL Server
Name: ODBC Driver 18 for SQL Server
```

## Step 3: Update Python Configuration

### Install Required Packages

```bash
pip install pyodbc
```

### Update .env File

Add SQL Server connection string to `.env`:

```env
# MongoDB (for staging)
MONGODB_URL=mongodb://localhost:27017

# SQL Server (for warehouse)
DATABASE_URL=mssql+pyodbc://user:password@server/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server

# Windows Authentication (recommended)
DATABASE_URL=mssql+pyodbc://@server/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server

# Or using localhost
DATABASE_URL=mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

### Connection String Examples

**Windows Authentication (Easiest)**
```
mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

**Named Instance**
```
mssql+pyodbc://@SERVER_NAME\SQLEXPRESS/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

**SQL Server Authentication**
```
mssql+pyodbc://sa:YourPassword123@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

**With Specific Port**
```
mssql+pyodbc://@localhost:1433/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

## Step 4: Test SQL Server Connection

### Test with PowerShell

```powershell
# Test basic connectivity
sqlcmd -S localhost -d TennisRankings -Q "SELECT @@VERSION"

# If using named instance
sqlcmd -S SERVER_NAME\SQLEXPRESS -d TennisRankings -Q "SELECT @@VERSION"
```

### Test with Python

Create test script:

```python
import pyodbc

connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=TennisRankings;Trusted_Connection=yes;"

try:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    print("✅ Connection successful!")
    print(cursor.fetchone())
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## Step 5: Verify Tables in SSMS

1. Open SSMS
2. Connect to `TennisRankings` database
3. Expand **TennisRankings** → **Tables**

You should see:
- ✅ Categories
- ✅ Competitions
- ✅ Complexes
- ✅ Venues
- ✅ Competitors
- ✅ Rankings
- ✅ Staging_Competitions
- ✅ Staging_Complexes
- ✅ Staging_Rankings
- ✅ ETL_ExecutionLog

## Step 6: Run ETL Pipeline

Once database is ready:

```bash
# Fetch API data → MongoDB
python api_test.py --with-mongodb

# Run ETL pipeline (MongoDB → SQL Server)
python -m tennis_etl.run_etl
```

## Step 7: Query Data in SSMS

After ETL completes, query the data:

```sql
-- View top 10 competitors
SELECT TOP 10 * FROM [TennisRankings].[dbo].[Competitors];

-- View latest rankings
SELECT TOP 10 * FROM [TennisRankings].[dbo].[Rankings]
ORDER BY [RankingDate] DESC, [Rank];

-- Count records by table
SELECT 
    'Categories' as TableName, COUNT(*) as RowCount FROM [dbo].[Categories]
UNION ALL
SELECT 'Competitions', COUNT(*) FROM [dbo].[Competitions]
UNION ALL
SELECT 'Complexes', COUNT(*) FROM [dbo].[Complexes]
UNION ALL
SELECT 'Venues', COUNT(*) FROM [dbo].[Venues]
UNION ALL
SELECT 'Competitors', COUNT(*) FROM [dbo].[Competitors]
UNION ALL
SELECT 'Rankings', COUNT(*) FROM [dbo].[Rankings];
```

## Troubleshooting

### "Cannot connect to server"

**Solution:**
```powershell
# Check if SQL Server is running
Get-Service MSSQLSERVER | Select-Object Status

# Start SQL Server if stopped
Start-Service MSSQLSERVER
```

### "Database does not exist"

**Solution:** Re-run the `create_tennis_warehouse.sql` script

### "Authentication failed"

**Solution:**
- Verify username/password (if using SQL Server auth)
- Use Windows Authentication (recommended)
- Check ODBC driver version matches your SQL Server version

### "ODBC Driver not found"

**Solution:**
```powershell
# Install ODBC driver
# Download: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
# Or use chocolatey
choco install sql-server-odbcdriver
```

### Python pyodbc import error

**Solution:**
```bash
pip install --upgrade pyodbc
```

## Common SSMS Actions

### Add New Database Login

```sql
-- Create SQL Server login
CREATE LOGIN [tennis_user] WITH PASSWORD = 'YourPassword123';

-- Create database user
CREATE USER [tennis_user] FOR LOGIN [tennis_user];

-- Grant permissions
ALTER ROLE [db_datareader] ADD MEMBER [tennis_user];
ALTER ROLE [db_datawriter] ADD MEMBER [tennis_user];
```

### View Database Backups

1. Right-click **TennisRankings** → **Properties**
2. Select **Files** to see data file locations
3. Select **Options** to set recovery model, etc.

### Create Database Backup

```sql
BACKUP DATABASE [TennisRankings] 
TO DISK = N'C:\Backups\TennisRankings_backup.bak'
WITH NOFORMAT, NOINIT, NAME = 'Full Backup', SKIP, NOREWIND, NOUNLOAD, STATS = 10;
```

## Architecture

```
┌─────────────────────┐
│  SportRadar API     │
└──────────┬──────────┘
           │ fetch JSON
           ▼
┌──────────────────────────┐
│  MongoDB (tennis_staging)│ ◄─── raw_competitions, raw_complexes, raw_rankings
└──────────┬───────────────┘
           │ ETL process
           ▼
┌──────────────────────────┐
│ SQL Server (TennisRankings)
│ ├─ Categories
│ ├─ Competitions
│ ├─ Complexes
│ ├─ Venues
│ ├─ Competitors
│ ├─ Rankings
│ └─ Staging_* & ETL_ExecutionLog
└──────────────────────────┘
```

## Next Steps

1. ✅ Create database in SSMS (using SQL script)
2. ✅ Update .env with connection string
3. ✅ Test connection with Python
4. ✅ Run ETL pipeline
5. ✅ Query data in SSMS
6. (Optional) Set up automated backups
7. (Optional) Configure monitoring/alerts

## Support

If you encounter issues:
1. Check SQL Server is running: `Get-Service MSSQLSERVER`
2. Verify connection string format
3. Check ODBC driver version
4. Review ETL logs in SQL Server: `SELECT * FROM [dbo].[ETL_ExecutionLog]`
5. Query staging tables for error details: `SELECT * FROM [dbo].[Staging_Rankings] WHERE [ProcessedFlag] = 0`
