# 📋 SQL Server SSMS 22 Integration - Quick Reference

## 🎯 What Was Created

I've set up a complete Tennis ETL pipeline with SQL Server database integration. Here's everything that was created:

### 📁 New Files

| File | Purpose |
|------|---------|
| `sql/create_tennis_warehouse.sql` | **Main** - SQL script to create database in SSMS (run this first!) |
| `SQL_SERVER_SETUP.md` | Detailed SQL Server setup instructions |
| `test_sqlserver.py` | Python script to test SQL Server connection |
| `diagnose_mongodb.py` | Python script to diagnose MongoDB issues |
| `COMPLETE_SETUP_GUIDE.md` | **Best** - Complete end-to-end setup guide |
| `MONGODB_ETL_GUIDE.md` | MongoDB integration details |
| `.env` | Updated with SQL Server connection examples |

### 🔧 Updated Files

| File | Changes |
|------|---------|
| `tennis_etl/database.py` | Added SQL Server support for upsert operations |
| `api_requests.py` | Added MongoDB storage integration |
| `api_test.py` | Added full pipeline test (API → MongoDB → ETL) |
| `requirements.txt` | Added python-dotenv and pyodbc packages |

## 🚀 Quick Start (5 Minutes)

### 1️⃣ Create Database in SSMS (2 minutes)

```
1. Open SQL Server Management Studio (SSMS)
2. Connect to your local server (Windows Auth)
3. File → Open → File
4. Select: sql/create_tennis_warehouse.sql
5. Click Execute (F5)
6. Wait for "✅ Database Setup Complete!" message
```

### 2️⃣ Update `.env` File (1 minute)

Edit `.env` and uncomment ONE of these:

```env
# Windows Auth (RECOMMENDED)
DATABASE_URL=mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

### 3️⃣ Test Connections (2 minutes)

```bash
# Test MongoDB
python diagnose_mongodb.py

# Test SQL Server
python test_sqlserver.py
```

Both should show ✅ success messages.

## 📊 Database Structure

### 10 Tables in TennisRankings Database

**Dimension Tables:**
- `Categories` - Tennis categories (ATP, WTA, etc.)
- `Competitions` - Tournament information
- `Complexes` - Tennis complex/facility information
- `Venues` - Individual venues within complexes
- `Competitors` - Tennis players

**Fact Table:**
- `Rankings` - Player rankings over time

**Staging Tables:**
- `Staging_Competitions` - Raw API data (for processing)
- `Staging_Complexes` - Raw API data (for processing)
- `Staging_Rankings` - Raw API data (for processing)

**Audit Table:**
- `ETL_ExecutionLog` - Pipeline execution history

## 🔄 ETL Pipeline Workflow

```
Step 1: Fetch API Data
  └─ python api_test.py --with-mongodb
  └─ Stores raw JSON in MongoDB

Step 2: Transform & Load to SQL Server
  └─ python -m tennis_etl.run_etl
  └─ Reads from MongoDB
  └─ Transforms data
  └─ Loads into SQL Server tables
  └─ Records execution in ETL_ExecutionLog
```

## 📖 Documentation Files

### For Different Scenarios:

1. **New to SQL Server?** → Start with `COMPLETE_SETUP_GUIDE.md`
   - Step-by-step instructions
   - Verification at each step
   - Troubleshooting section

2. **Need SQL Server details?** → Read `SQL_SERVER_SETUP.md`
   - SSMS instructions
   - Connection string formats
   - ODBC driver info

3. **Need MongoDB details?** → Read `MONGODB_ETL_GUIDE.md`
   - Data flow explanation
   - Storage/retrieval functions
   - Architecture diagrams

4. **Connection problems?** → Run diagnostic scripts:
   - `python test_sqlserver.py`
   - `python diagnose_mongodb.py`

## 🔗 Connection String Options

### Windows Authentication (Easiest ✅)
```
DATABASE_URL=mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

### Named Instance
```
DATABASE_URL=mssql+pyodbc://@SERVER_NAME\SQLEXPRESS/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

### SQL Server Auth
```
DATABASE_URL=mssql+pyodbc://sa:YourPassword@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server
```

## 🧪 Testing Commands

### Check MongoDB
```bash
python diagnose_mongodb.py
```
Shows: ✅ Connection status, collections, row counts

### Check SQL Server
```bash
python test_sqlserver.py
```
Shows: ✅ Connection status, tables, row counts

### Test Full Pipeline
```bash
python api_test.py --with-mongodb
```
Shows: ✅ API fetch, MongoDB storage, retrieval

### Run ETL
```bash
python -m tennis_etl.run_etl
```
Populates SQL Server tables from MongoDB data

## 📊 Querying Data in SSMS

After ETL completes, you can query in SSMS:

```sql
-- Top competitors
SELECT TOP 10 FullName, Country FROM Competitors;

-- Latest rankings
SELECT TOP 10 c.FullName, r.Rank, r.RankingDate
FROM Rankings r
JOIN Competitors c ON r.CompetitorID = c.CompetitorID
ORDER BY r.RankingDate DESC;

-- Row counts
SELECT 'Categories', COUNT(*) FROM Categories
UNION ALL SELECT 'Rankings', COUNT(*) FROM Rankings;
```

## ⚠️ Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Cannot connect to SQL Server" | `Start-Service MSSQLSERVER` |
| "Database does not exist" | Re-run `create_tennis_warehouse.sql` |
| "ODBC Driver not found" | Install from Microsoft or use `choco install sql-server-odbcdriver` |
| "Authentication failed" | Use Windows Auth or check credentials |
| "MongoDB connection error" | Check `diagnose_mongodb.py` output |

## 📝 Files You'll Use Most Often

1. **First Time Setup:**
   - `sql/create_tennis_warehouse.sql` (run in SSMS)
   - `COMPLETE_SETUP_GUIDE.md` (follow along)

2. **Daily Use:**
   - `python api_test.py --with-mongodb` (fetch data)
   - `python -m tennis_etl.run_etl` (process data)

3. **Troubleshooting:**
   - `test_sqlserver.py` (verify SQL Server)
   - `diagnose_mongodb.py` (verify MongoDB)

4. **Reference:**
   - `SQL_SERVER_SETUP.md` (SQL Server questions)
   - `MONGODB_ETL_GUIDE.md` (data flow questions)

## 🎓 Architecture Overview

```
┌─────────────────────┐
│  SportRadar API     │
│  (Tennis Data)      │
└──────────┬──────────┘
           ↓ (fetch JSON)
┌─────────────────────┐
│ MongoDB Staging     │
│ (raw data cache)    │
└──────────┬──────────┘
           ↓ (ETL transforms)
┌─────────────────────┐
│ SQL Server SSMS 22  │
│ (data warehouse)    │
│ - Analytics         │
│ - Reporting         │
│ - Dashboards        │
└─────────────────────┘
```

## 💡 Pro Tips

1. **Windows Auth is easiest** - No password management
2. **Use diagnose scripts first** - They'll tell you what's wrong
3. **Check ETL_ExecutionLog** - See what succeeded/failed
4. **Keep MongoDB running** - It's the staging layer
5. **Backup your database** - Important data!

## 🔗 Useful Links

- [SSMS 2022 Download](https://learn.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms)
- [ODBC Driver Download](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- [SQL Server Connection Strings](https://www.connectionstrings.com/sql-server/)
- [MongoDB Python Driver](https://docs.mongodb.com/drivers/pymongo/)

## 📞 When in Doubt

1. Run `python test_sqlserver.py` - diagnoses SQL Server issues
2. Run `python diagnose_mongodb.py` - diagnoses MongoDB issues
3. Check the `COMPLETE_SETUP_GUIDE.md` - step-by-step instructions
4. Look at ETL logs: `SELECT * FROM [dbo].[ETL_ExecutionLog]`

## ✅ You're All Set!

Your Tennis ETL pipeline is ready to:
- ✅ Fetch data from SportRadar API
- ✅ Store raw data in MongoDB
- ✅ Transform and normalize the data
- ✅ Load into SQL Server warehouse
- ✅ Query and analyze in SSMS

**Next steps:**
1. Run `python test_sqlserver.py` to verify setup
2. Run `python api_test.py --with-mongodb` to fetch data
3. Run `python -m tennis_etl.run_etl` to process it
4. Query your data in SSMS!

---

**Questions?** Check the markdown files or run the diagnostic scripts - they'll guide you! 🚀
