#  ETL & Data Migration Test Suite - User Guide

**File:** `sql/ETL_TEST_SUITE.sql`  
**Purpose:** Comprehensive testing for data migration and ETL validation  
**Status:** Production-Ready  
**Last Updated:** June 2, 2026

---

##  Test Coverage Summary

| Category | Tests | Purpose |
|----------|-------|---------|
| **1. Sanity Tests** | 5 | Verify schema exists and has data |
| **2. Regression Tests** | 3 | Ensure data completeness & accuracy |
| **3. Referential Integrity** | 5 | FK constraint validation |
| **4. Data Quality** | 5 | Business rule validation |
| **5. Dimensional Analysis** | 5 | Dimension table completeness |
| **6. Fact Table Analysis** | 5 | Metrics validation |
| **7. SCD Type 2 Validation** | 4 | Historical tracking verification |
| **8. Performance Tests** | 3 | Query response time benchmarks |
| **9. Reconciliation Tests** | 3 | Source vs Target comparison |
| **10. Audit Trail Validation** | 3 | ETL metadata tracking |
| **TOTAL** | **41 Tests** | Full ETL validation |

---

##  How to Execute

### Option 1: Run Entire Test Suite (Recommended)

```sql
-- In SQL Server Management Studio (SSMS):
1. File → Open → sql/ETL_TEST_SUITE.sql
2. Press F5 or click "Execute"
3. View Results tab for output
```

**Execution Time:** 2-5 minutes (depends on data volume)

### Option 2: Run Individual Tests

Copy/paste specific test blocks from the file based on what you want to validate.

### Option 3: Schedule as SQL Agent Job

```sql
-- Create SQL Agent job to run nightly
USE msdb;
GO

EXEC dbo.sp_add_job
    @job_name = 'ETL_Test_Suite_Nightly',
    @enabled = 1
GO

EXEC sp_add_jobstep
    @job_name = 'ETL_Test_Suite_Nightly',
    @step_name = 'Run_ETL_Tests',
    @command = N'EXEC xp_cmdshell ''sqlcmd -S YOUR_SERVER -d TennisRankings -i C:\scripts\ETL_TEST_SUITE.sql''',
    @database_name = 'TennisRankings'
GO

EXEC sp_add_schedule
    @schedule_name = 'Daily_2AM',
    @freq_type = 4,  -- Daily
    @freq_interval = 1,
    @active_start_time = 020000  -- 2:00 AM
GO

EXEC sp_attach_schedule
    @job_name = 'ETL_Test_Suite_Nightly',
    @schedule_name = 'Daily_2AM'
GO
```

---

##  Understanding Test Results

### Status Indicators

| Symbol | Meaning | Action |
|--------|---------|--------|
| [PASS] PASS | Test passed | No action needed |
| [WARNING] WARNING | Test passed but threshold warning | Monitor/investigate |
| [FAIL] FAIL | Test failed | Fix immediately |

### Example Output

```
+-------------------------------------------------------------+
| SANITY TESTS - Table Existence & Row Counts                 |
+-------------------------------------------------------------+

[PASS] All dimension tables exist
[PASS] FACT_Rankings table exists
[PASS] Staging tables exist
[PASS] FACT_Rankings has data (45,678 rows)

TableName               RowCount
-----------------------------------
FACT_Rankings          45,678
DIM_Competitor         12,345
DIM_Time               18,250
...
```

---

##  Test Details

### **1. SANITY TESTS**

**What They Check:**
- All required tables exist in schema
- Tables contain data
- Basic row count validation

**Pass Criteria:**
- [PASS] All dimension & fact tables exist
- [PASS] FACT_Rankings has > 0 rows
- [PASS] Reference dimensions populated

**Action if Failed:**
```
[FAIL] Missing dimension tables
   → Execute: sql/STAR_SCHEMA_DDL.sql
   
[FAIL] FACT_Rankings is empty
   → Run: python -m tennis_etl.ingestion_pipeline
```

---

### **2. REGRESSION TESTS**

**What They Check:**
- Data completeness vs baseline
- Record counts meet minimum thresholds
- Data distribution by category

**Pass Criteria:**
- [PASS] Categories ≥ 5
- [PASS] Competitors ≥ 100
- [PASS] Facts ≥ 100

**Sample Output:**
```
Expected Baseline Counts:
  • Categories (minimum 5): 6 [PASS] PASS
  • Current Competitors (minimum 100): 2,450 [PASS] PASS
  • Current Facts (minimum 100): 45,678 [PASS] PASS
```

**Action if Failed:**
```
[WARNING] Baseline not met
   → Check if first-time load (adjust thresholds)
   → Verify ETL completed successfully
   → Check if data is recent (not stale)
```

---

### **3. REFERENTIAL INTEGRITY TESTS**

**What They Check:**
- No orphaned fact records (missing dimensions)
- FK constraints are valid
- All referenced dimensions exist

**Pass Criteria:**
- [PASS] Orphaned competitor records = 0
- [PASS] Orphaned time records = 0
- [PASS] Orphaned category records = 0

**Action if Failed:**
```
[FAIL] Found 50 orphaned fact records (missing competitor)
   → Investigate source data quality
   → Run: 
     DELETE FROM FACT_Rankings 
     WHERE CompetitorKey NOT IN (SELECT CompetitorKey FROM DIM_Competitor)
   → Re-run ETL for affected data
```

---

### **4. DATA QUALITY TESTS**

**What They Check:**
- All ranks are positive (>0)
- Points are non-negative (≥0)
- Win percentages are 0-100
- Flags contain only valid values (Y/N)

**Pass Criteria:**
- [PASS] Invalid ranks = 0
- [PASS] Invalid points = 0
- [PASS] Invalid win % = 0
- [PASS] Invalid flags = 0

**Sample Output:**
```
[PASS] All ranks are positive (>0)
[PASS] All points are non-negative
[PASS] All win_percentages are within valid range (0-100)
[PASS] All flag values are valid (Y/N only)
```

**Action if Failed:**
```
[FAIL] Found 25 invalid ranks (≤0)
   → Data quality issue in source system
   → Investigate SportRadar API response
   → Quarantine bad records:
     UPDATE FACT_Rankings 
     SET IsCurrentFlag = 'N' 
     WHERE Rank <= 0
```

---

### **5. DIMENSIONAL ANALYSIS**

**What They Check:**
- Dimension table completeness
- SCD Type 2 integrity
- No orphaned dimension records

**Pass Criteria:**
- [PASS] Competitor SCD2 integrity valid (no violations)
- [PASS] Competition SCD2 integrity valid (no violations)
- [PASS] All foreign key relationships valid

**Sample Output:**
```
DIM_Time                        18,250 rows (50 years of dates)
DIM_Category                         6 rows (ATP, WTA, Challenger...)
DIM_Country                        195 rows (All countries)
DIM_Competitor SCD2 Status:
  • Current Versions:     2,450
  • Historical Versions:     347
  • Unique Competitors:    2,450
```

**Action if Failed:**
```
[FAIL] Found 5 DIM_Competitor SCD2 violations
   → Multiple current versions for same competitor
   → Fix:
     UPDATE DIM_Competitor
     SET IsCurrentFlag = 'N', ExpiryDate = GETDATE()
     WHERE IsCurrentFlag = 'Y'
       AND CompetitorSID IN (
         SELECT CompetitorSID 
         FROM DIM_Competitor 
         GROUP BY CompetitorSID 
         HAVING COUNT(CASE WHEN IsCurrentFlag='Y' THEN 1 END) > 1
       )
```

---

### **6. FACT TABLE ANALYSIS**

**What They Check:**
- Metric distribution (Rank, Points, Competitions Played)
- No duplicate rankings (grain uniqueness)
- Metrics within expected range

**Pass Criteria:**
- [PASS] No duplicate rankings (grain is unique)
- [PASS] Rank range: 1-5000 (typical)
- [PASS] Points range: 0-15000 (typical)

**Sample Output:**
```
Total Records:              45,678
Current Snapshots:          45,678
Historical Snapshots:            0
Unique Competitors:          2,450
Unique Dates:                   18
Date Range:       20260601 - 20260618

Rank Statistics:
  Min: 1, Avg: 892, Max: 5234, StdDev: 1245

Points Statistics:
  Min: 0, Avg: 3456, Max: 12850, StdDev: 2891
```

**Action if Failed:**
```
[FAIL] Found 12 duplicate rankings (grain not unique)
   → Issue: Same competitor, category, time appears multiple times
   → Investigate: Why ETL loaded same data twice?
   → Fix: 
     DELETE FROM FACT_Rankings 
     WHERE RankingFactKey NOT IN (
       SELECT MIN(RankingFactKey)
       FROM FACT_Rankings
       GROUP BY CompetitorKey, CategoryKey, TimeKey
     )
```

---

### **7. SCD TYPE 2 VALIDATION**

**What They Check:**
- Historical tracking is correct
- Effective/expiry date logic
- Current flag logic

**Pass Criteria:**
- [PASS] All effective dates < expiry dates
- [PASS] Current flag = 'Y' has NULL expiry
- [PASS] Current flag = 'N' has valid expiry

**Sample Output:**
```
Competitor History:
  Unique Competitors:     2,450
  Total Versions:         2,797  (347 historical versions)
  Has Current Version:        1
  Historical Versions:      347

Competition History:
  Unique Competitions:    1,234
  Total Versions:         1,298  (64 historical versions)
  Has Current Version:        1
  Historical Versions:       64

Sample Changes (Top 3):
  sr:competitor:2504 → "Novak Djokovic" → Changed name
  sr:competitor:3012 → "Carlos Alcaraz" → Country updated
```

---

### **8. PERFORMANCE TESTS**

**What They Check:**
- Query response times
- Index usage efficiency
- Execution plans

**Pass Criteria:**
- [PASS] Top 10 query: < 1 second
- [PASS] Category summary: < 1 second
- [PASS] History query: < 2 seconds

**Sample Output:**
```
Benchmark 8.1: Top 10 ATP Players Query
(1) Rows affected by INSERT/UPDATE/DELETE: 10
 Table 'DIM_Competitor'. Scan count 0, logical reads 5, physical reads 0
 Table 'FACT_Rankings'. Scan count 1, logical reads 12, physical reads 0
 Execution time: 0.234 seconds [PASS] PASS

Benchmark 8.2: Category Summary Aggregation
 Table 'FACT_Rankings'. Scan count 1, logical reads 45, physical reads 0
 Execution time: 0.567 seconds [PASS] PASS

Benchmark 8.3: Competitor Ranking History
 Execution time: 1.234 seconds [PASS] PASS
```

**Action if Failed:**
```
[WARNING] Query took 5.2 seconds (> 2s threshold)
   → Rebuild indexes:
     ALTER INDEX ALL ON FACT_Rankings REBUILD
     ALTER INDEX ALL ON DIM_Competitor REBUILD
   
   → Update statistics:
     UPDATE STATISTICS FACT_Rankings
     UPDATE STATISTICS DIM_Competitor
   
   → Check execution plan for missing indexes
```

---

### **9. RECONCILIATION TESTS**

**What They Check:**
- Staging records fully processed
- Source vs target record counts match
- Data load timeline

**Pass Criteria:**
- [PASS] Unprocessed staging records = 0
- [PASS] All records marked processed
- [PASS] Load counts reconcile

**Sample Output:**
```
Staging Table Status:
  • Unprocessed records: 0 [PASS] PASS
  • Processed records:   45,678 [PASS] PASS

ETL Load History:
  • Batches Loaded: 18
  • First Load Time: 2026-05-18 14:23:45
  • Last Load Time:  2026-06-02 09:15:30

Source System Distribution:
  SourceSystem    RecordCount    UniqueCompetitors    EarliestLoad            LatestLoad
  SportRadar           45,678             2,450         2026-05-18 14:23:45   2026-06-02 09:15:30
```

**Action if Failed:**
```
[WARNING] 1,234 unprocessed staging records
   → Records failed ETL processing
   → Check STG_Rankings_Raw for error details:
     SELECT * FROM STG_Rankings_Raw 
     WHERE IsProcessedFlag = 'N'
   
   → Re-run ETL for affected batch
```

---

### **10. AUDIT TRAIL VALIDATION**

**What They Check:**
- ETL metadata completeness
- Batch tracking
- Data freshness

**Pass Criteria:**
- [PASS] All records have created_at, updated_at
- [PASS] All records have source_system, batch_id
- [PASS] Data not stale (≤ 1 day old)

**Sample Output:**
```
Audit Columns Status:
  Total Records:        45,678
  Missing CreatedAt:         0 [PASS]
  Missing UpdatedAt:         0 [PASS]
  Missing SourceSystem:      0 [PASS]
  Missing BatchID:           0 [PASS]

ETL Batch Tracking (Top 5):
  ETLBatchID         LoadedAt              RecordsLoaded  UniqueCompetitors  UniqueDates
  20260602_BATCH     2026-06-02 09:15:30        2,890           450              18
  20260601_BATCH     2026-06-01 08:42:15        2,765           425              17
  20260531_BATCH     2026-05-31 07:33:02        2,834           440              18

Data Freshness:
  • Latest data date: 2026-06-02
  • Days old: 0 [PASS] PASS (data is current)
```

**Action if Failed:**
```
[FAIL] Data is stale (25 days old)
   → No recent ETL runs
   → Check ETL scheduler status
   → Manual run required:
     python -m tennis_etl.ingestion_pipeline

[FAIL] Missing audit columns (12 records)
   → Data loaded without proper audit trail
   → Not recommended for production
   → Investigate ETL loader code
```

---

##  Interpreting Results

### Color-Coded Summary

```
[PASS] GREEN (PASS)
   → All tests passed, data is ready for production
   → No action needed
   → Continue monitoring

[WARNING] YELLOW (WARNING)
   → Tests passed but with concerns
   → Monitor the metric
   → Investigate root cause
   → May need attention within SLA

[FAIL] RED (FAIL)
   → Test failed, critical issue
   → Fix immediately before production use
   → Investigate root cause
   → Prevent data corruption/loss
```

---

##  Troubleshooting Guide

### Common Issues & Solutions

#### Issue: "Orphaned fact records (missing competitor)"

```sql
-- Find the orphaned records
SELECT TOP 10 *
FROM FACT_Rankings
WHERE CompetitorKey NOT IN (SELECT CompetitorKey FROM DIM_Competitor)

-- Option 1: Delete orphaned records
DELETE FROM FACT_Rankings
WHERE CompetitorKey NOT IN (SELECT CompetitorKey FROM DIM_Competitor)

-- Option 2: Investigate why competitor was deleted
SELECT * FROM DIM_Competitor WHERE IsCurrentFlag = 'N'
```

#### Issue: "Found duplicate rankings"

```sql
-- Find duplicates
SELECT CompetitorKey, CategoryKey, TimeKey, COUNT(*) cnt
FROM FACT_Rankings
GROUP BY CompetitorKey, CategoryKey, TimeKey
HAVING COUNT(*) > 1

-- Remove duplicates (keep first occurrence)
DELETE FROM FACT_Rankings
WHERE RankingFactKey NOT IN (
    SELECT MIN(RankingFactKey)
    FROM FACT_Rankings
    GROUP BY CompetitorKey, CategoryKey, TimeKey
)
```

#### Issue: "SCD2 violations in DIM_Competitor"

```sql
-- Find competitors with multiple current versions
SELECT CompetitorSID, COUNT(*) cnt
FROM DIM_Competitor
WHERE IsCurrentFlag = 'Y'
GROUP BY CompetitorSID
HAVING COUNT(*) > 1

-- Fix: Keep latest, mark others as historical
WITH RankedCompetitors AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY CompetitorSID ORDER BY EffectiveDate DESC) rn
    FROM DIM_Competitor
    WHERE IsCurrentFlag = 'Y'
)
UPDATE RankedCompetitors
SET IsCurrentFlag = 'N', ExpiryDate = GETDATE()
WHERE rn > 1
```

#### Issue: "Query performance degraded"

```sql
-- Rebuild all indexes
ALTER INDEX ALL ON FACT_Rankings REBUILD
ALTER INDEX ALL ON DIM_Competitor REBUILD
ALTER INDEX ALL ON DIM_Competition REBUILD

-- Update statistics
UPDATE STATISTICS FACT_Rankings
UPDATE STATISTICS DIM_Competitor
UPDATE STATISTICS DIM_Competition

-- Check fragmentation
SELECT 
    OBJECT_NAME(ips.object_id) AS TableName,
    i.name AS IndexName,
    ips.avg_fragmentation_in_percent AS Fragmentation
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
INNER JOIN sys.indexes i ON ips.object_id = i.object_id 
    AND ips.index_id = i.index_id
WHERE ips.avg_fragmentation_in_percent > 10
```

---

##  Test Execution Checklist

- [ ] All sanity tests pass
- [ ] No orphaned fact records
- [ ] No data quality violations
- [ ] SCD2 integrity valid
- [ ] Query performance acceptable
- [ ] Audit trail complete
- [ ] Data is fresh (≤ 1 day)
- [ ] Staging records fully processed
- [ ] No duplicate rankings
- [ ] All dimensions reconcile

---

##  Recommended Test Schedule

| Frequency | When | What |
|-----------|------|------|
| **Daily** | After each ETL run | Sanity, Regression, Data Quality tests |
| **Weekly** | Every Monday | Full suite including performance |
| **Monthly** | Month-end | Full suite + reconciliation report |
| **Quarterly** | Each quarter | Comprehensive audit + optimization |

---

##  Support

**Questions about a specific test?**
- Refer to the test section above
- Check the "Action if Failed" guidance
- Review troubleshooting guide

**Need to modify thresholds?**
- Edit baseline values in Test 2.1
- Update performance targets in Test 8
- Adjust data freshness SLA in Test 10.3

---

**Last Updated:** June 2, 2026  
**Status:** Ready for Production  
**Version:** 1.0


