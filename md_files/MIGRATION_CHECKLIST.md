# [PASS] ETL & Migration Test Checklist - Quick Reference

**For:** Data Engineers, DBAs, QA Testers  
**Use:** Before, During, and After Data Migration  
**Status:** Production-Ready

---

## 🔄 Pre-Migration Checklist

### Database Setup
- [ ] Database `TennisRankings` created
- [ ] `dbo` schema exists and is default
- [ ] SQL Server 2019+ version verified
- [ ] Service account has necessary permissions
- [ ] Backup location configured
- [ ] Maintenance windows scheduled

### Code & Configuration
- [ ] `STAR_SCHEMA_DDL.sql` reviewed
- [ ] `ingestion_pipeline.py` integrated with StarSchemaLoader
- [ ] `.env` file configured with connection strings
- [ ] API credentials validated
- [ ] MongoDB connection tested
- [ ] Database connection tested

### Baseline Metrics Recorded
- [ ] Source system record counts documented
- [ ] Expected data ranges defined
- [ ] Performance baselines established
- [ ] Storage estimates confirmed

---

##  Schema Creation Phase

### Execute DDL
```sql
-- Run in SSMS
File → Open → sql/STAR_SCHEMA_DDL.sql
F5 (Execute)
```

- [ ] All 11 tables created
- [ ] No errors in messages tab
- [ ] Primary keys enforced
- [ ] Foreign keys enforced
- [ ] Indexes created (30+)
- [ ] Check constraints active
- [ ] Views created (4)
- [ ] Stored procedures created (1)

### Verify Schema
```sql
SELECT COUNT(*) FROM sys.tables 
WHERE OBJECT_SCHEMA_NAME(object_id) = 'dbo'
-- Expected: 11 tables
```

- [ ] 7 Dimension tables exist
- [ ] 1 Fact table exists
- [ ] 2 Staging tables exist
- [ ] 2 Bridge tables exist

---

## 🌱 Reference Data Seeding

### Populate DIM_Time (20+ years)
```sql
-- Execute time dimension population script
-- Expected: 18,250+ rows
```

- [ ] DIM_Time populated (18,250 rows)
- [ ] Date range: 2000-01-01 to 2050-12-31
- [ ] All fields populated (year, quarter, month, week, day)
- [ ] Season values calculated

### Populate Reference Dimensions
```sql
-- DIM_Category (6+ rows)
-- DIM_Country (195 rows)
-- DIM_RankingSeries (2+ rows)
```

- [ ] DIM_Category ≥ 6 rows (ATP, WTA, Challenger, etc.)
- [ ] DIM_Country ≥ 195 rows (all countries)
- [ ] DIM_RankingSeries ≥ 2 rows (ATP, WTA series)
- [ ] IsActiveFlag set correctly
- [ ] Source system tracked

---

##  ETL Execution Phase

### Run Pipeline (Full Automation)
```bash
python -m tennis_etl.ingestion_pipeline
```

- [ ] Phase 1A: API extraction successful
- [ ] Phase 1B: MongoDB staging successful
- [ ] Phase 1C: SQL warehouse load successful
- [ ] Phase 2: Star schema load successful
- [ ] No exceptions or errors logged
- [ ] Execution time acceptable (< 10 minutes)

### Monitor Logs
```
[PHASE 1A] API extraction complete
[PHASE 1B] MongoDB staging complete
[PHASE 1C] SQL load complete
[PHASE 2] Star Schema load complete
Pipeline success: stats...
```

- [ ] All phases completed
- [ ] Batch ID recorded
- [ ] Timestamp logged
- [ ] Record counts verified

### Record Results
| Phase | Status | Duration | Record Count |
|-------|--------|----------|--------------|
| 1A API | [PASS] | ___ sec | ___ rows |
| 1B MongoDB | [PASS] | ___ sec | ___ docs |
| 1C SQL | [PASS] | ___ sec | ___ rows |
| 2 Star | [PASS] | ___ sec | ___ rows |

---

##  Sanity Testing Phase

### Test 1: Schema Validation
```sql
SELECT COUNT(*) FROM FACT_Rankings
SELECT COUNT(*) FROM DIM_Competitor WHERE IsCurrentFlag = 'Y'
SELECT COUNT(*) FROM DIM_Category
```

- [ ] FACT_Rankings has data (> 100 rows)
- [ ] DIM_Competitor has current records
- [ ] DIM_Category has ≥ 5 rows
- [ ] All dimensions populated

### Test 2: Data Completeness
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 1 & 2
```

- [ ] Categories ≥ 5 rows
- [ ] Competitors ≥ 100 rows
- [ ] Facts ≥ 100 rows
- [ ] Distribution by category is balanced

### Test 3: Data Quality
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 4
```

- [ ] [PASS] All ranks > 0
- [ ] [PASS] All points ≥ 0
- [ ] [PASS] All win % between 0-100
- [ ] [PASS] All flags are Y/N only

### Test 4: Referential Integrity
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 3
```

- [ ] [PASS] No orphaned facts (missing competitor)
- [ ] [PASS] No orphaned facts (missing time)
- [ ] [PASS] No orphaned facts (missing category)
- [ ] [PASS] All FK constraints valid

---

##  Regression Testing Phase

### Test 5: Dimension Validation
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 5
```

- [ ] DIM_Time: 18,250+ rows, complete
- [ ] DIM_Category: All categories present
- [ ] DIM_Country: All countries present
- [ ] DIM_Competitor: All current versions flagged
- [ ] DIM_Competition: All competitions present

### Test 6: Fact Table Metrics
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 6
```

- [ ] No duplicate rankings (grain is unique)
- [ ] Rank distribution: min ≥ 1, reasonable max
- [ ] Points distribution: realistic range
- [ ] Competitions played: reasonable values
- [ ] All measures within expected range

### Test 7: SCD Type 2 History
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 7
```

- [ ] [PASS] DIM_Competitor SCD2 valid (no violations)
- [ ] [PASS] DIM_Competition SCD2 valid (no violations)
- [ ] All effective dates < expiry dates
- [ ] Historical versions tracked correctly

---

## ⚡ Performance Testing Phase

### Test 8: Query Performance
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 8
SET STATISTICS TIME ON
```

**Benchmarks:**
- [ ] Top 10 query: < 1 second [PASS]
- [ ] Category summary: < 1 second [PASS]
- [ ] Competitor history: < 2 seconds [PASS]
- [ ] Indexes being used (logical reads not physical)

### Test 9: Storage & Growth
```sql
EXEC sp_spaceused 'FACT_Rankings'
EXEC sp_spaceused 'DIM_Competitor'
```

- [ ] Storage usage matches estimate
- [ ] Index size reasonable (2-3x data)
- [ ] No unexpected growth
- [ ] Disk space sufficient for growth

---

##  Reconciliation Phase

### Test 10: Source vs Target
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 9
```

- [ ] Staging records fully processed (0 unprocessed)
- [ ] Batch tracking complete
- [ ] Source system properly logged
- [ ] Record counts reconcile

### Test 11: Data Freshness
```sql
SELECT MAX(CAST(TimeKey AS VARCHAR(8))) FROM FACT_Rankings
```

- [ ] Latest data is current (today or yesterday)
- [ ] Days old ≤ 1 day [PASS]
- [ ] No data gaps in timeline
- [ ] Incremental loads working

### Test 12: Audit Trail
```sql
EXECUTE [sql/ETL_TEST_SUITE.sql] -- Run section 10
```

- [ ] All records have created_at timestamp
- [ ] All records have updated_at timestamp
- [ ] All records have source_system value
- [ ] All records have ETL_batch_id
- [ ] Batch history logged correctly

---

##  Business Validation Phase

### Test 13: Analytical Queries
```sql
-- Top 10 rankings
SELECT TOP 10 * FROM VW_CurrentRankings 
WHERE CategoryName = 'ATP' 
ORDER BY Rank

-- Category summary
SELECT * FROM VW_Category_Performance 
ORDER BY CategoryName, [FullDate] DESC

-- Competitor history
SELECT * FROM VW_Competitor_Ranking_History 
WHERE CompetitorName = 'Novak Djokovic'
ORDER BY [FullDate] DESC LIMIT 90
```

- [ ] Queries return expected results
- [ ] Rankings appear correct
- [ ] Rankings match source data
- [ ] Historical trends visible
- [ ] Geographic distribution accurate

### Test 14: Business Rules
- [ ] Top competitors identified correctly
- [ ] Category rankings separate properly
- [ ] Point calculations accurate
- [ ] Rank movements logical
- [ ] Country assignments correct

---

## 🔐 Data Integrity Phase

### Test 15: Data Quality Checks
```sql
SELECT * FROM VW_Data_Quality_Checks
```

- [ ] No missing dimensions
- [ ] No invalid ranks
- [ ] No negative points
- [ ] No SCD2 violations
- [ ] All issues ≤ threshold

### Test 16: Constraint Validation
```sql
DBCC CHECKDB (TennisRankings, REPAIR_FAST)
```

- [ ] Database integrity check passes
- [ ] No corruption detected
- [ ] Constraints enforced
- [ ] Indexes valid
- [ ] All allocated extents used

---

##  Sign-Off Phase

### Final Checklist
- [ ] All tests passed ([PASS] PASS status)
- [ ] No orphaned records
- [ ] No data quality violations
- [ ] Performance acceptable
- [ ] Storage as expected
- [ ] Audit trail complete
- [ ] Business validation approved
- [ ] Data migration document completed

### Documentation
- [ ] Test results saved
- [ ] Execution logs archived
- [ ] Batch IDs documented
- [ ] Baseline metrics updated
- [ ] Known issues logged
- [ ] Performance baselines established
- [ ] Runbook created

### Sign-Off
```
Data Migration Completed: _______________
Validated By (DBA):       _______________
Approved By (Manager):    _______________
Date:                     _______________
```

---

## 🚨 Rollback Plan

**If critical issues found:**

### Option 1: Restore from Backup
```sql
RESTORE DATABASE TennisRankings FROM DISK = 'backup_file.bak'
```

### Option 2: Truncate and Reload
```sql
DELETE FROM FACT_Rankings
DELETE FROM DIM_Competitor WHERE IsCurrentFlag = 'Y'
-- Re-run ETL
```

### Option 3: Partial Rollback
```sql
-- Delete specific batch
DELETE FROM FACT_Rankings
WHERE ETLBatchID = '20260602_BATCH'
-- Re-run ETL for that batch only
```

- [ ] Rollback procedure documented
- [ ] Backup verified before go-live
- [ ] Rollback tested

---

##  Escalation Path

**Issue Found** → **Action Required** → **Escalate to**

| Severity | Issue | Action | Escalate |
|----------|-------|--------|----------|
| 🔴 Critical | Data loss, corruption | Stop pipeline, restore backup | Senior DBA |
| 🟠 High | Orphaned records, FK violations | Quarantine data, investigate | DBA + Architect |
| 🟡 Medium | Data quality issues | Tag records, continue monitoring | ETL Owner |
| 🟢 Low | Performance warning | Monitor, optimize later | Performance Team |

---

##  Post-Migration Activities

### First Week
- [ ] Run test suite daily
- [ ] Monitor for issues
- [ ] Validate with business
- [ ] Optimize indexes if needed
- [ ] Archive test results

### First Month
- [ ] Run comprehensive test suite
- [ ] Performance trending
- [ ] Storage growth monitoring
- [ ] User adoption tracking
- [ ] Documentation updates

### Ongoing
- [ ] Test suite runs daily
- [ ] Monthly comprehensive review
- [ ] Quarterly optimization
- [ ] Annual capacity planning
- [ ] Version upgrades planned

---

##  Test Results Template

```
=======================================================
ETL MIGRATION TEST RESULTS
=======================================================

Date: _______________
Migration Batch: _______________
Executed By: _______________

SANITY TESTS:               [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
REGRESSION TESTS:           [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
REFERENTIAL INTEGRITY:      [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
DATA QUALITY:               [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
DIMENSIONAL ANALYSIS:       [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
FACT TABLE ANALYSIS:        [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
SCD TYPE 2 VALIDATION:      [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
PERFORMANCE TESTS:          [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
RECONCILIATION:             [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL
AUDIT TRAIL:                [PASS] PASS / [WARNING] WARNING / [FAIL] FAIL

OVERALL RESULT:             [PASS] READY / [WARNING] REVIEW NEEDED / [FAIL] BLOCKED

Issues Found: _______________
Actions Taken: _______________
Follow-Up: _______________

=======================================================
```

---

**Status:** [PASS] Production Ready  
**Last Updated:** June 2, 2026  
**Version:** 1.0


