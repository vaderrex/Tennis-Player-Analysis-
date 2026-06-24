# 🎾 Tennis Rankings Star Schema - Implementation Guide

**Date:** June 2, 2026  
**Status:** Complete and Production-Ready  
**Target Databases:** SQL Server 2019+ | PostgreSQL 14+ | Snowflake

---

## 📋 Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| **STAR_SCHEMA_DESIGN.md** | Complete star schema architecture & business analysis | Architects, Data Engineers |
| **STAR_SCHEMA_DDL.sql** | Production DDL (SQL Server optimized) | DBAs, SQL Engineers |
| **star_schema_loader.py** | Python ETL implementation | Python Developers, Data Engineers |
| **This Guide** | Step-by-step implementation | Everyone |

---

## 🏗️ What Was Delivered

### 1. **Complete Star Schema Design** (`STAR_SCHEMA_DESIGN.md`)

Includes:
- ✅ Business process & grain analysis
- ✅ Entity relationship diagram (conceptual)
- ✅ 8 dimension tables + 1 fact table + 2 bridge tables
- ✅ SCD Type 2 handling (Competitor, Competition)
- ✅ Production-grade DDL with constraints
- ✅ 4 analytical views for reporting
- ✅ 1 stored procedure for ETL loading
- ✅ Data quality validation framework

### 2. **SQL Server DDL** (`sql/STAR_SCHEMA_DDL.sql`)

**Production-Ready Components:**
- 7 Dimension Tables (properly indexed)
- 1 Fact Table (optimized for analytics)
- 2 Bridge Tables (M:M relationships)
- 2 Staging Tables (ETL processing)
- 4 Reporting Views (pre-built dashboarding)
- 1 Stored Procedure (data loading)
- 1 Data Quality Validation View

**Key Features:**
- All PK/FK constraints enforced
- 20+ indexes optimized for typical queries
- Check constraints for data quality at load time
- SCD Type 2 logic for dimension history
- Audit trail (created_at, updated_at, source_system, etl_batch_id)

### 3. **Python ETL Loader** (`tennis_etl/star_schema_loader.py`)

**Class: StarSchemaLoader**
- Handles SCD Type 2 upserts
- Dimension reconciliation
- Fact table inserts with referential integrity
- Data quality validation
- Full audit trail tracking

**Methods:**
```python
loader = StarSchemaLoader(database_url)
stats = loader.load_rankings(
    ranking_date='2026-06-02',
    batch_id='BATCH_20260602',
    source_system='SportRadar'
)
```

---

## 🚀 Step-by-Step Implementation

### PHASE 1: Database Setup (5-10 minutes)

#### Step 1A: Create Database (SQL Server)

**Option 1: GUI (SSMS)**
```
1. Open SQL Server Management Studio
2. Right-click "Databases" → "New Database"
3. Name: TennisRankings
4. Accept defaults, click OK
```

**Option 2: T-SQL**
```sql
CREATE DATABASE TennisRankings
GO
USE TennisRankings
GO
```

#### Step 1B: Execute Star Schema DDL

```sql
-- In SSMS:
1. File → Open → sql/STAR_SCHEMA_DDL.sql
2. Press F5 or click "Execute"
3. Wait for completion (should see ✅ messages)
```

Expected output:
```
========== CREATING DIMENSION TABLES ==========
✅ DIM_Time table created
✅ DIM_Category table created
✅ DIM_Country table created
...
========== ✅ STAR SCHEMA CREATION COMPLETE ==========
```

#### Step 1C: Seed Reference Data

```sql
-- Populate DIM_Time with 20+ years of dates
DECLARE @StartDate DATE = '2000-01-01'
DECLARE @EndDate DATE = '2050-12-31'
DECLARE @CurrentDate DATE = @StartDate

WHILE @CurrentDate <= @EndDate
BEGIN
    DECLARE @TimeKey INT = CAST(FORMAT(@CurrentDate, 'yyyyMMdd') AS INT)
    
    IF NOT EXISTS (SELECT 1 FROM DIM_Time WHERE TimeKey = @TimeKey)
    BEGIN
        INSERT INTO DIM_Time (
            TimeKey, FullDate, Year, Quarter, Month, Week, Day, DayOfWeek,
            DayName, IsWeekend, WeekStartDate, MonthStartDate, 
            QuarterStartDate, YearStartDate, SourceSystem
        )
        VALUES (
            @TimeKey,
            @CurrentDate,
            YEAR(@CurrentDate),
            DATEPART(QUARTER, @CurrentDate),
            MONTH(@CurrentDate),
            DATEPART(WEEK, @CurrentDate),
            DAY(@CurrentDate),
            DATEPART(WEEKDAY, @CurrentDate),
            FORMAT(@CurrentDate, 'dddd'),
            CASE WHEN DATEPART(WEEKDAY, @CurrentDate) IN (1, 7) THEN 'Y' ELSE 'N' END,
            DATEFROMPARTS(YEAR(@CurrentDate), MONTH(@CurrentDate), 1),
            DATEFROMPARTS(YEAR(@CurrentDate), MONTH(@CurrentDate), 1),
            DATEFROMPARTS(YEAR(@CurrentDate), (DATEPART(QUARTER, @CurrentDate)-1)*3+1, 1),
            DATEFROMPARTS(YEAR(@CurrentDate), 1, 1),
            'SYSTEM'
        )
    END
    
    SET @CurrentDate = DATEADD(DAY, 1, @CurrentDate)
END

SELECT COUNT(*) AS TotalDays FROM DIM_Time WHERE Year >= 2020 AND Year <= 2030
-- Expected: ~3,652 rows
```

```sql
-- Populate DIM_Category
INSERT INTO DIM_Category (CategoryKey, CategorySID, CategoryName, IsProFlag, SourceSystem)
VALUES
    (1, 'sr:category:3', 'ATP', 'Y', 'SportRadar'),
    (2, 'sr:category:6', 'WTA', 'Y', 'SportRadar'),
    (3, 'sr:category:72', 'Challenger', 'Y', 'SportRadar'),
    (4, 'sr:category:181', 'Hopman Cup', 'Y', 'SportRadar'),
    (5, 'sr:category:76', 'Davis Cup', 'N', 'SportRadar'),
    (6, 'sr:category:74', 'Billie Jean King Cup', 'N', 'SportRadar')
GO

-- Verify
SELECT COUNT(*) FROM DIM_Category
-- Expected: 6 rows
```

```sql
-- Populate DIM_Country
INSERT INTO DIM_Country (CountryKey, CountryCode, CountryName, Region, SourceSystem)
VALUES
    (1, 'US', 'United States', 'North America', 'GEO_DB'),
    (2, 'GB', 'United Kingdom', 'Europe', 'GEO_DB'),
    (3, 'FR', 'France', 'Europe', 'GEO_DB'),
    (4, 'DE', 'Germany', 'Europe', 'GEO_DB'),
    (5, 'AU', 'Australia', 'Oceania', 'GEO_DB'),
    (6, 'JP', 'Japan', 'Asia', 'GEO_DB'),
    (7, 'CN', 'China', 'Asia', 'GEO_DB'),
    (8, 'BR', 'Brazil', 'South America', 'GEO_DB'),
    (9, 'RU', 'Russia', 'Europe', 'GEO_DB'),
    (10, 'ES', 'Spain', 'Europe', 'GEO_DB')
GO

-- Verify
SELECT COUNT(*) FROM DIM_Country
-- Expected: 10 rows (expand as needed)
```

```sql
-- Create default Ranking Series
INSERT INTO DIM_RankingSeries (
    RankingSeriesKey, SeriesSID, SeriesName, SeriesType, 
    SourceSystem, IsActiveFlag, EffectiveDate
)
VALUES
    (1, 'SR_ATP_CURRENT', 'ATP Current Rankings', 'Current', 'SportRadar', 'Y', '2000-01-01'),
    (2, 'SR_WTA_CURRENT', 'WTA Current Rankings', 'Current', 'SportRadar', 'Y', '2000-01-01')
GO

-- Verify
SELECT * FROM DIM_RankingSeries WHERE IsActiveFlag = 'Y'
```

---

### PHASE 2: ETL Integration (10-15 minutes)

#### Step 2A: Load Python Module

```python
# In your existing pipeline, import the new loader
from tennis_etl.star_schema_loader import StarSchemaLoader

# Initialize
loader = StarSchemaLoader(
    database_url='mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server'
)
```

#### Step 2B: Populate Staging Tables

Your existing `ingestion_pipeline.py` should populate `STG_Rankings_Raw` from MongoDB:

```python
# Existing code: Extract from MongoDB, transform, insert into staging
for ranking_group in mongo_db['raw_rankings'].find():
    for item in ranking_group.get('competitor_rankings', []):
        competitor = item.get('competitor', {})
        
        stg_record = {
            'CompetitorSID': competitor.get('id'),
            'CompetitorName': competitor.get('name'),
            'CategorySID': ranking_group.get('category_id'),
            'Rank': item.get('rank'),
            'Points': item.get('points'),
            'Movement': item.get('movement'),
            'CompetitionsPlayed': item.get('competitions_played'),
            'RankingDate': datetime.now().date(),
            'SourceSystem': 'SportRadar',
            'ExtractedAt': datetime.now(),
            'IsProcessedFlag': 'N'
        }
        
        # Insert into STG_Rankings_Raw
        insert_staging(stg_record)
```

#### Step 2C: Run ETL Loader

```python
# After staging is populated, run the loader
from datetime import datetime

ranking_date = datetime.now().date()
batch_id = ranking_date.strftime('%Y%m%d_BATCH')

stats = loader.load_rankings(
    ranking_date=ranking_date,
    batch_id=batch_id,
    source_system='SportRadar'
)

print(f"✅ ETL Complete!")
print(f"  Facts Loaded: {stats.facts_loaded}")
print(f"  Dimensions Created: {stats.dimensions_created}")
print(f"  Execution Time: {stats.execution_time_seconds:.2f}s")
```

---

### PHASE 3: Validation & Testing (5-10 minutes)

#### Step 3A: Validate Schema

```sql
-- Check all tables exist
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'dbo'
  AND TABLE_NAME LIKE 'DIM_%' OR TABLE_NAME LIKE 'FACT_%'
ORDER BY TABLE_NAME
```

Expected result:
```
BRIDGE_Competitor_Competition
DIM_Category
DIM_Competition
DIM_Competitor
DIM_Country
DIM_RankingSeries
DIM_Time
DIM_Venue
FACT_Rankings
STG_Competitor_Changes
STG_Rankings_Raw
```

#### Step 3B: Run Data Quality Checks

```sql
-- Check for data quality issues
SELECT * FROM VW_Data_Quality_Checks
```

Expected output (all should be 0):
```
TableName              CheckType                    IssueCount
FACT_Rankings          Missing Dimensions           0
FACT_Rankings          Invalid Rank                 0
FACT_Rankings          Negative Points              0
DIM_Competitor         SCD Type 2 Violation         0
DIM_Competition        SCD Type 2 Violation         0
```

#### Step 3C: Test Reporting Views

```sql
-- Current Rankings View
SELECT TOP 10
    CompetitorName,
    CategoryName,
    Rank,
    Points,
    RankMovement,
    RankingDate
FROM VW_CurrentRankings
WHERE CategoryName = 'ATP'
ORDER BY Rank
```

```sql
-- Category Performance
SELECT
    CategoryName,
    [FullDate],
    TotalCompetitors,
    AvgRank,
    MaxPoints
FROM VW_Category_Performance
ORDER BY [FullDate] DESC
```

---

## 🎯 Typical Queries & Analytics

### Top 10 ATP Players

```sql
SELECT TOP 10
    CompetitorName,
    CountryName,
    Rank,
    Points,
    CompetitionsPlayed
FROM VW_CurrentRankings
WHERE CategoryName = 'ATP'
ORDER BY Rank
```

### Competitor's Ranking History

```sql
SELECT
    CompetitorName,
    FullDate,
    Rank,
    Points,
    RankMovement,
    PreviousRank,
    (PreviousRank - Rank) AS RankChangeFromPrevious
FROM VW_Competitor_Ranking_History
WHERE CompetitorName = 'Novak Djokovic'
  AND FullDate >= DATEADD(MONTH, -6, GETDATE())
ORDER BY FullDate DESC
```

### Category Trends Over Time

```sql
SELECT
    CategoryName,
    YEAR([FullDate]) AS Year,
    MONTH([FullDate]) AS Month,
    COUNT(DISTINCT Competitor) AS UniqueCompetitors,
    AVG(CAST(Rank AS FLOAT)) AS AvgRank,
    MAX(Points) AS MaxPoints,
    MIN(Points) AS MinPoints
FROM VW_Category_Performance
WHERE YEAR([FullDate]) >= 2025
GROUP BY CategoryName, YEAR([FullDate]), MONTH([FullDate])
ORDER BY CategoryName, Year DESC, Month DESC
```

### Top Movers (Rank Improvement)

```sql
SELECT TOP 20
    dc.CompetitorName,
    dco.CountryName,
    dcat.CategoryName,
    MAX(fr.Rank) AS WorstRank,
    MIN(fr.Rank) AS BestRank,
    MAX(fr.Rank) - MIN(fr.Rank) AS RankImprovement,
    COUNT(DISTINCT fr.TimeKey) AS RankingPeriods
FROM FACT_Rankings fr
INNER JOIN DIM_Competitor dc ON fr.CompetitorKey = dc.CompetitorKey
INNER JOIN DIM_Country dco ON dc.CountryKey = dco.CountryKey
INNER JOIN DIM_Category dcat ON fr.CategoryKey = dcat.CategoryKey
WHERE dc.IsCurrentFlag = 'Y'
  AND fr.TimeKey >= (SELECT MIN(TimeKey) FROM DIM_Time WHERE FullDate >= DATEADD(MONTH, -3, GETDATE()))
GROUP BY dc.CompetitorKey, dc.CompetitorName, dco.CountryName, dcat.CategoryName
HAVING MAX(fr.Rank) - MIN(fr.Rank) >= 10
ORDER BY RankImprovement DESC
```

### Geographic Distribution

```sql
SELECT
    dco.CountryName,
    dco.Region,
    dcat.CategoryName,
    COUNT(DISTINCT fr.CompetitorKey) AS CompetitorCount,
    AVG(CAST(fr.Rank AS FLOAT)) AS AvgRank
FROM FACT_Rankings fr
INNER JOIN DIM_Competitor dc ON fr.CompetitorKey = dc.CompetitorKey
INNER JOIN DIM_Country dco ON dc.CountryKey = dco.CountryKey
INNER JOIN DIM_Category dcat ON fr.CategoryKey = dcat.CategoryKey
WHERE fr.IsCurrentFlag = 'Y'
  AND dc.IsCurrentFlag = 'Y'
GROUP BY dco.CountryName, dco.Region, dcat.CategoryName
ORDER BY CompetitorCount DESC
```

---

## 🔄 Maintenance & Operations

### Daily ETL Run

```bash
# In your scheduler (cron/Windows Task Scheduler):
python -m tennis_etl.star_schema_loader \
  --database-url "mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server" \
  --ranking-date $(date +%Y-%m-%d) \
  --batch-id "DAILY_$(date +%Y%m%d)"
```

### Monitor ETL Performance

```sql
-- Check load statistics
SELECT
    ETLBatchID,
    LoadedAt,
    COUNT(*) AS RecordsLoaded,
    MAX(Rank) AS HighestRank,
    MIN(Rank) AS LowestRank,
    AVG(CAST(Points AS FLOAT)) AS AvgPoints
FROM FACT_Rankings
WHERE LoadedAt >= DATEADD(DAY, -7, GETDATE())
GROUP BY ETLBatchID, LoadedAt
ORDER BY LoadedAt DESC
```

### Rebuild Indexes (Monthly)

```sql
ALTER INDEX ALL ON FACT_Rankings REBUILD
DBCC SHRINKDB (TennisRankings)
```

### Backup Star Schema

```sql
-- Full backup
BACKUP DATABASE TennisRankings
TO DISK = 'C:\Backups\TennisRankings_Full.bak'
WITH COMPRESSION

-- Incremental backup (weekly)
BACKUP DATABASE TennisRankings
TO DISK = 'C:\Backups\TennisRankings_Diff.bak'
WITH DIFFERENTIAL, COMPRESSION
```

---

## 🐛 Troubleshooting

### Issue: FK Constraint Violation

**Symptom:** `The INSERT, UPDATE, or DELETE statement conflicted with a FOREIGN KEY constraint`

**Solution:**
```sql
-- Check for orphaned records
SELECT TOP 100 *
FROM FACT_Rankings
WHERE CompetitorKey NOT IN (SELECT CompetitorKey FROM DIM_Competitor)
```

### Issue: Slow Fact Table Queries

**Symptom:** `SELECT * FROM FACT_Rankings WHERE TimeKey = 20260602` takes > 5 seconds

**Solution:**
```sql
-- Rebuild indexes
ALTER INDEX ALL ON FACT_Rankings REBUILD

-- Update statistics
UPDATE STATISTICS FACT_Rankings
```

### Issue: SCD Type 2 Duplicates

**Symptom:** Competitor appears multiple times with IsCurrentFlag = 'Y'

**Solution:**
```sql
-- Fix: Mark all but latest as expired
WITH RankedCompetitors AS (
    SELECT
        CompetitorKey,
        CompetitorSID,
        ROW_NUMBER() OVER (PARTITION BY CompetitorSID ORDER BY EffectiveDate DESC) AS rn
    FROM DIM_Competitor
    WHERE IsCurrentFlag = 'Y'
)
UPDATE DIM_Competitor
SET IsCurrentFlag = 'N', ExpiryDate = GETDATE()
WHERE CompetitorKey IN (
    SELECT CompetitorKey FROM RankedCompetitors WHERE rn > 1
)
```

---

## 📚 References

### SQL Server Documentation
- [SQL Server Data Types](https://learn.microsoft.com/en-us/sql/t-sql/data-types/data-types-transact-sql)
- [CREATE TABLE](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-table-transact-sql)
- [CREATE INDEX](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql)

### Star Schema Best Practices
- [The Data Warehouse Toolkit](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/) (Kimball Group)
- [Slowly Changing Dimensions](https://en.wikipedia.org/wiki/Slowly_changing_dimension)
- [Fact Table Grain](https://www.kimballgroup.com/2008/10/fact-table-grain/)

### Tennis Rankings Data
- [SportRadar API Documentation](https://developer.sportradar.com/files/indexDocs)
- [ATP Rankings System](https://www.atptour.com/)
- [WTA Rankings System](https://www.wtatennis.com/)

---

## ✅ Validation Checklist

Before going to production:

- [ ] All 11 tables created and accessible
- [ ] DIM_Time populated with 20+ years of dates
- [ ] DIM_Category, DIM_Country, DIM_RankingSeries seeded
- [ ] At least 1 complete ETL run executed successfully
- [ ] Data quality checks show 0 issues
- [ ] Reporting views query in < 5 seconds
- [ ] Backup strategy configured
- [ ] Monitoring alerts set up
- [ ] Documentation reviewed by DBA
- [ ] Production deployment approved

---

## 🎓 Next Steps

### Short-term (Week 1)
1. ✅ Execute Star Schema DDL
2. ✅ Seed reference dimensions
3. ✅ Run first ETL load
4. ✅ Validate with test queries

### Medium-term (Week 2-4)
1. ✅ Integrate ETL with existing pipeline
2. ✅ Build Tableau/PowerBI dashboards
3. ✅ Configure automated daily loads
4. ✅ Set up monitoring & alerting

### Long-term (Month 2+)
1. ✅ Expand to other sports data
2. ✅ Implement advanced analytics (ML models)
3. ✅ Multi-dimensional drill-down
4. ✅ Real-time rankings system

---

**Questions?** Refer to `STAR_SCHEMA_DESIGN.md` for architectural details or contact your data engineering team.

