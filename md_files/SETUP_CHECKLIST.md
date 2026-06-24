# ✅ SQL Server ETL Setup Checklist

Use this checklist to ensure your Tennis ETL pipeline is fully configured and working.

## 📋 Pre-Setup Requirements

### System Requirements
- [ ] Windows 10/11 or Windows Server
- [ ] SQL Server 2022 (or 2019+) installed
- [ ] SQL Server Management Studio (SSMS) 22 installed
- [ ] Python 3.9+ installed
- [ ] MongoDB running locally or accessible

### Access & Permissions
- [ ] Admin access to Windows (can run services)
- [ ] Permission to create databases in SQL Server
- [ ] Python virtual environment activated (.venv)

---

## 🗄️ Step 1: Create SQL Server Database

### In SSMS:
- [ ] Open SQL Server Management Studio
- [ ] Connect to your local server
- [ ] Open `sql/create_tennis_warehouse.sql` script
- [ ] Execute the script (F5)
- [ ] See "✅ Database Setup Complete!" message

### Verification:
- [ ] In Object Explorer, see "TennisRankings" database
- [ ] Expand TennisRankings → Tables
- [ ] See all 10 tables:
  - [ ] Categories
  - [ ] Competitors
  - [ ] Complexes
  - [ ] Competitions
  - [ ] ETL_ExecutionLog
  - [ ] Rankings
  - [ ] Staging_Competitions
  - [ ] Staging_Complexes
  - [ ] Staging_Rankings
  - [ ] Venues

---

## 🔐 Step 2: Configure Environment

### Update `.env` File:
- [ ] Open `.env` in editor
- [ ] Verify SPORTRADAR_API_KEY is set
- [ ] Uncomment ONE DATABASE_URL (Windows Auth recommended):
  ```env
  DATABASE_URL=mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
  ```
- [ ] Save `.env` file
- [ ] Do NOT commit `.env` to git (contains credentials)

### Verify `.env` Has:
- [ ] SPORTRADAR_API_KEY (from SportRadar)
- [ ] SPORTRADAR_ACCESS_LEVEL=trial
- [ ] DATABASE_URL (SQL Server connection)
- [ ] MONGODB_URL=mongodb://localhost:27017

---

## 📦 Step 3: Install Dependencies

### Install Required Packages:
```bash
pip install -r requirements.txt
pip install pyodbc
```

### Verify Installation:
- [ ] No error messages during installation
- [ ] Can import pyodbc: `python -c "import pyodbc; print('OK')"`
- [ ] Can import sqlalchemy: `python -c "import sqlalchemy; print('OK')"`
- [ ] Can import pymongo: `python -c "import pymongo; print('OK')"`

---

## 🔌 Step 4: Test Connections

### Test MongoDB:
```bash
python diagnose_mongodb.py
```

Checklist:
- [ ] ✅ MongoDB connection successful
- [ ] ✅ tennis_staging database found (may be empty)
- [ ] ✅ No authentication errors

### Test SQL Server:
```bash
python test_sqlserver.py
```

Checklist:
- [ ] ✅ SQL Server connection successful
- [ ] ✅ TennisRankings database found
- [ ] ✅ All 10 tables found
- [ ] ✅ pyodbc installed and working
- [ ] ✅ ODBC Driver 17 or 18 available

### If Tests Fail:
- [ ] Check SQL Server is running: `Get-Service MSSQLSERVER`
- [ ] Check MongoDB is running: `Get-Service MongoDB` or `docker ps`
- [ ] Verify `.env` DATABASE_URL is correct
- [ ] Check ODBC drivers installed

---

## 🚀 Step 5: Run ETL Pipeline

### Step 5a: Fetch API Data
```bash
python api_test.py --with-mongodb
```

Checklist:
- [ ] ✅ "API Response received" message
- [ ] ✅ "Data stored in MongoDB" message
- [ ] ✅ "Successfully retrieved from MongoDB" message
- [ ] ✅ No error messages

### Step 5b: Verify MongoDB Data
```bash
python diagnose_mongodb.py
```

Checklist:
- [ ] ✅ raw_competitions: X documents (X > 0)
- [ ] ✅ raw_complexes: Y documents (Y > 0)
- [ ] ✅ raw_rankings: Z documents (Z > 0)

If counts are 0:
- [ ] Re-run `python api_test.py --with-mongodb`

### Step 5c: Run ETL Transforms
```bash
python -m tennis_etl.run_etl
```

Checklist:
- [ ] ✅ "Retrieved competitions from MongoDB"
- [ ] ✅ "Transformed competitions data"
- [ ] ✅ "Loaded X records" messages
- [ ] ✅ "ETL Pipeline Completed Successfully!"
- [ ] ✅ No error messages
- [ ] ✅ No database constraint errors

### Step 5d: Verify SQL Server Data
```bash
python test_sqlserver.py
```

Checklist:
- [ ] ✅ Categories: N rows (N > 0)
- [ ] ✅ Competitions: M rows (M > 0)
- [ ] ✅ Complexes: L rows (L > 0)
- [ ] ✅ Venues: K rows (K > 0)
- [ ] ✅ Competitors: J rows (J > 0)
- [ ] ✅ Rankings: I rows (I > 0)

---

## 📊 Step 6: Query Data in SSMS

### Run Test Queries:

```sql
-- Check Categories
USE [TennisRankings];
SELECT COUNT(*) as CategoryCount FROM [Categories];
```
- [ ] ✅ Returns a number > 0

```sql
-- Check Competitors
SELECT COUNT(*) as CompetitorCount FROM [Competitors];
```
- [ ] ✅ Returns a number > 0

```sql
-- Check Rankings
SELECT COUNT(*) as RankingCount FROM [Rankings];
```
- [ ] ✅ Returns a number > 0

```sql
-- View sample data
SELECT TOP 5 FullName, Country FROM [Competitors];
```
- [ ] ✅ Shows tennis player names

### View ETL Log
```sql
SELECT * FROM [ETL_ExecutionLog] ORDER BY [StartTime] DESC;
```
- [ ] ✅ Shows successful ETL execution(s)
- [ ] ✅ Status = 'Completed' or 'Running'
- [ ] ✅ TotalRecordsProcessed > 0

---

## 🔄 Step 7: Verify Pipeline Integration

### Data Flow Check:

```
API → MongoDB → SQL Server
```

Run this command to verify all three steps:

```bash
# Step 1: Fetch from API
python api_test.py --with-mongodb
```
- [ ] ✅ API data fetched
- [ ] ✅ Data stored in MongoDB

```bash
# Step 2: Check MongoDB
python diagnose_mongodb.py
```
- [ ] ✅ Data in MongoDB collections

```bash
# Step 3: Transform to SQL Server
python -m tennis_etl.run_etl
```
- [ ] ✅ Data loaded to SQL Server

```bash
# Step 4: Verify SQL Server
python test_sqlserver.py
```
- [ ] ✅ Data in SQL Server tables

---

## 🎯 Verification Summary

All checks should show ✅:

### Infrastructure
- [ ] ✅ SQL Server running and accessible
- [ ] ✅ MongoDB running and accessible
- [ ] ✅ Python environment configured
- [ ] ✅ All packages installed

### Database
- [ ] ✅ TennisRankings database exists in SQL Server
- [ ] ✅ All 10 tables created
- [ ] ✅ Stored procedures created

### Configuration
- [ ] ✅ .env file configured
- [ ] ✅ DATABASE_URL points to TennisRankings
- [ ] ✅ SPORTRADAR_API_KEY configured
- [ ] ✅ MongoDB URL configured

### Pipeline
- [ ] ✅ API can fetch data from SportRadar
- [ ] ✅ Data stored successfully in MongoDB
- [ ] ✅ ETL transforms data correctly
- [ ] ✅ Data loads into SQL Server
- [ ] ✅ Data is queryable in SSMS

### Data Quality
- [ ] ✅ Categories table has data
- [ ] ✅ Competitors table has data
- [ ] ✅ Rankings table has data
- [ ] ✅ No error records in staging tables

---

## 📝 Common Issues & Solutions

### SQL Server Connection Issues

**Problem:** "Cannot connect to server"
- [ ] Verify SQL Server is running: `Get-Service MSSQLSERVER | Select Status`
- [ ] Start SQL Server: `Start-Service MSSQLSERVER`
- [ ] Try connection string with specific server name

**Problem:** "Database does not exist"
- [ ] Re-run `create_tennis_warehouse.sql` in SSMS
- [ ] Verify no errors during creation

**Problem:** "ODBC Driver not found"
- [ ] Install ODBC Driver 17 for SQL Server from Microsoft website
- [ ] Or use: `choco install sql-server-odbcdriver`

### MongoDB Issues

**Problem:** "Cannot connect to MongoDB"
- [ ] Verify MongoDB is running: `Get-Service MongoDB | Select Status`
- [ ] Start MongoDB: `Start-Service MongoDB`
- [ ] Check MongoDB is on localhost:27017

**Problem:** "No data in MongoDB after API fetch"
- [ ] Re-run: `python api_test.py --with-mongodb`
- [ ] Check for error messages
- [ ] Verify SPORTRADAR_API_KEY is correct

### ETL Issues

**Problem:** "No data loaded to SQL Server"
- [ ] Verify data is in MongoDB: `python diagnose_mongodb.py`
- [ ] Check for errors in ETL output
- [ ] Review ETL_ExecutionLog in SQL Server

**Problem:** "ETL fails with constraint error"
- [ ] Check ETL_ExecutionLog for details: `SELECT * FROM [ETL_ExecutionLog]`
- [ ] Verify primary key uniqueness in staging data
- [ ] May need to clear staging tables and retry

---

## 🎉 Success Criteria

### ✅ You're Done When:

- [ ] All three diagnostic scripts pass (test_sqlserver.py, diagnose_mongodb.py)
- [ ] SQL Server shows > 0 rows in all tables
- [ ] MongoDB has > 0 documents in staging collections
- [ ] SSMS queries return expected data
- [ ] ETL_ExecutionLog shows successful runs

### 📊 Expected Rows (After One ETL Run):

- [ ] Categories: 2-20 rows
- [ ] Competitors: 100-1000 rows
- [ ] Competitions: 10-50 rows
- [ ] Rankings: 500-5000 rows

---

## 📚 Documentation Reference

If you need more details, see:

| Document | When to Read |
|----------|--------------|
| COMPLETE_SETUP_GUIDE.md | Step-by-step walkthrough |
| SQL_SERVER_SETUP.md | SQL Server specific questions |
| MONGODB_ETL_GUIDE.md | Data flow and architecture |
| SQL_SERVER_QUICK_REFERENCE.md | Quick lookup reference |

---

## 🚀 Next Steps After Completion

1. **Schedule automated runs** (optional)
   - Use Windows Task Scheduler
   - Or Python scheduler library

2. **Set up monitoring** (optional)
   - Monitor ETL_ExecutionLog
   - Alert on failures

3. **Create dashboards** (optional)
   - Use Power BI
   - Connect to SQL Server TennisRankings database

4. **Backup database** (recommended)
   - Regular SQL Server backups
   - Store backup in safe location

---

## ✨ You're All Set!

Once all checkboxes are marked ✅, your Tennis ETL pipeline is:
- **Fully configured** ✅
- **Properly tested** ✅
- **Ready for production** ✅

You can now:
- Run `python api_test.py --with-mongodb` to fetch latest data
- Run `python -m tennis_etl.run_etl` to process it
- Query results in SSMS
- Schedule regular updates

**Happy analyzing!** 🎾📊
