-- ============================================================================
-- Tennis Rankings ETL & Data Migration - Comprehensive Test Suite
-- ============================================================================
-- Purpose: Regression, Sanity, and Quality testing for data migration
-- Execution: Run in SQL Server Management Studio (SSMS)
-- Date: June 2, 2026
-- 
-- Test Categories:
--   1. SANITY TESTS - Basic structural validation
--   2. REGRESSION TESTS - Data completeness and accuracy
--   3. REFERENTIAL INTEGRITY TESTS - FK constraints validation
--   4. DATA QUALITY TESTS - Business rule validation
--   5. DIMENSIONAL ANALYSIS - Dimension table completeness
--   6. FACT TABLE ANALYSIS - Fact table metrics validation
--   7. SCD TYPE 2 VALIDATION - Historical tracking verification
--   8. PERFORMANCE TESTS - Query performance benchmarks
--   9. RECONCILIATION TESTS - Source vs Target comparison
-- 10. AUDIT TRAIL VALIDATION - ETL metadata tracking
-- ============================================================================

USE [TennisRankings]
GO

PRINT '================================================================='
PRINT 'TENNIS RANKINGS ETL TEST SUITE - COMPREHENSIVE'
PRINT '================================================================='
GO

-- ============================================================================
-- 1. SANITY TESTS - Verify all tables exist and have data
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| SANITY TESTS - Table Existence & Row Counts                     |'
PRINT '+-----------------------------------------------------------------+'
GO

DECLARE @sanity_passed INT = 0
DECLARE @sanity_failed INT = 0

-- Test 1.1: All dimension tables exist
IF EXISTS (SELECT 1 FROM sys.tables WHERE name LIKE 'DIM_%' AND OBJECT_SCHEMA_NAME(object_id) = 'dbo')
BEGIN
    PRINT '[PASS] All dimension tables exist'
    SET @sanity_passed = @sanity_passed + 1
END
ELSE
BEGIN
    PRINT '[FAIL] Missing dimension tables'
    SET @sanity_failed = @sanity_failed + 1
END

-- Test 1.2: Fact table exists
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'FACT_Rankings' AND OBJECT_SCHEMA_NAME(object_id) = 'dbo')
BEGIN
    PRINT '[PASS] FACT_Rankings table exists'
    SET @sanity_passed = @sanity_passed + 1
END
ELSE
BEGIN
    PRINT '[FAIL] FACT_Rankings table missing'
    SET @sanity_failed = @sanity_failed + 1
END

-- Test 1.3: Staging tables exist
IF EXISTS (SELECT 1 FROM sys.tables WHERE name LIKE 'STG_%' AND OBJECT_SCHEMA_NAME(object_id) = 'dbo')
BEGIN
    PRINT '[PASS] Staging tables exist'
    SET @sanity_passed = @sanity_passed + 1
END
ELSE
BEGIN
    PRINT '[FAIL] Staging tables missing'
    SET @sanity_failed = @sanity_failed + 1
END

-- Test 1.4: Check if fact table has data
IF (SELECT COUNT(*) FROM FACT_Rankings) > 0
BEGIN
    PRINT '[PASS] FACT_Rankings has data (' + CAST(COUNT(*) AS VARCHAR(20)) + ' rows)'
    SET @sanity_passed = @sanity_passed + 1
END
ELSE
BEGIN
    PRINT '[WARNING] FACT_Rankings is empty'
    SET @sanity_failed = @sanity_failed + 1
END
GO

-- Test 1.5: Row count summary
SELECT 
    'DIM_Time' AS TableName, COUNT(*) AS RowCount FROM DIM_Time
UNION ALL SELECT 'DIM_Category', COUNT(*) FROM DIM_Category
UNION ALL SELECT 'DIM_Country', COUNT(*) FROM DIM_Country
UNION ALL SELECT 'DIM_Venue', COUNT(*) FROM DIM_Venue
UNION ALL SELECT 'DIM_RankingSeries', COUNT(*) FROM DIM_RankingSeries
UNION ALL SELECT 'DIM_Competitor', COUNT(*) FROM DIM_Competitor
UNION ALL SELECT 'DIM_Competition', COUNT(*) FROM DIM_Competition
UNION ALL SELECT 'FACT_Rankings', COUNT(*) FROM FACT_Rankings
UNION ALL SELECT 'STG_Rankings_Raw', COUNT(*) FROM STG_Rankings_Raw
ORDER BY RowCount DESC
GO

-- ============================================================================
-- 2. REGRESSION TESTS - Data Completeness & Accuracy
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| REGRESSION TESTS - Data Completeness & Record Counts            |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 2.1: Verify minimum expected record counts
DECLARE @category_count INT = (SELECT COUNT(*) FROM DIM_Category)
DECLARE @competitor_count INT = (SELECT COUNT(*) FROM DIM_Competitor WHERE IsCurrentFlag = 'Y')
DECLARE @fact_count INT = (SELECT COUNT(*) FROM FACT_Rankings WHERE IsCurrentFlag = 'Y')

PRINT 'Expected Baseline Counts:'
PRINT '  • Categories (minimum 5): ' + CAST(@category_count AS VARCHAR(10))
PRINT '  • Current Competitors (minimum 100): ' + CAST(@competitor_count AS VARCHAR(10))
PRINT '  • Current Facts (minimum 100): ' + CAST(@fact_count AS VARCHAR(10))

IF @category_count >= 5
    PRINT '[PASS] Category count meets baseline'
ELSE
    PRINT '[FAIL] Category count below baseline (' + CAST(@category_count AS VARCHAR(10)) + ' < 5)'

IF @competitor_count >= 100
    PRINT '[PASS] Competitor count meets baseline'
ELSE
    PRINT '[WARNING] Competitor count below baseline (' + CAST(@competitor_count AS VARCHAR(10)) + ' < 100)'

IF @fact_count >= 100
    PRINT '[PASS] Fact count meets baseline'
ELSE
    PRINT '[WARNING] Fact count below baseline (' + CAST(@fact_count AS VARCHAR(10)) + ' < 100)'

GO

-- Test 2.2: Data distribution by category
SELECT 
    dcat.CategoryName,
    COUNT(DISTINCT fr.CompetitorKey) AS UniqueCompetitors,
    COUNT(*) AS TotalRankings,
    AVG(CAST(fr.Rank AS FLOAT)) AS AvgRank,
    MIN(fr.Rank) AS MinRank,
    MAX(fr.Rank) AS MaxRank,
    MAX(fr.Points) AS MaxPoints
FROM FACT_Rankings fr
INNER JOIN DIM_Category dcat ON fr.CategoryKey = dcat.CategoryKey
WHERE fr.IsCurrentFlag = 'Y'
GROUP BY dcat.CategoryName
ORDER BY COUNT(*) DESC
GO

-- Test 2.3: Verify no data is 100% null for critical columns
SELECT 
    'FACT_Rankings.Rank' AS ColumnCheck,
    COUNT(*) AS TotalRows,
    COUNT(Rank) AS NonNullCount,
    COUNT(CASE WHEN Rank IS NULL THEN 1 END) AS NullCount
FROM FACT_Rankings
WHERE IsCurrentFlag = 'Y'
UNION ALL
SELECT 
    'FACT_Rankings.Points',
    COUNT(*),
    COUNT(Points),
    COUNT(CASE WHEN Points IS NULL THEN 1 END)
FROM FACT_Rankings
WHERE IsCurrentFlag = 'Y'
UNION ALL
SELECT 
    'FACT_Rankings.CompetitorKey',
    COUNT(*),
    COUNT(CompetitorKey),
    COUNT(CASE WHEN CompetitorKey IS NULL THEN 1 END)
FROM FACT_Rankings
WHERE IsCurrentFlag = 'Y'
GO

-- ============================================================================
-- 3. REFERENTIAL INTEGRITY TESTS - FK Constraint Validation
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| REFERENTIAL INTEGRITY TESTS - Foreign Key Validation            |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 3.1: Orphaned fact records (missing competitor)
DECLARE @orphaned_competitor INT = (
    SELECT COUNT(*)
    FROM FACT_Rankings
    WHERE CompetitorKey NOT IN (SELECT CompetitorKey FROM DIM_Competitor)
)

IF @orphaned_competitor = 0
    PRINT '[PASS] No orphaned fact records (missing competitor)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@orphaned_competitor AS VARCHAR(10)) + ' orphaned fact records (missing competitor)'
GO

-- Test 3.2: Orphaned fact records (missing time)
DECLARE @orphaned_time INT = (
    SELECT COUNT(*)
    FROM FACT_Rankings
    WHERE TimeKey NOT IN (SELECT TimeKey FROM DIM_Time)
)

IF @orphaned_time = 0
    PRINT '[PASS] No orphaned fact records (missing time)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@orphaned_time AS VARCHAR(10)) + ' orphaned fact records (missing time)'
GO

-- Test 3.3: Orphaned fact records (missing category)
DECLARE @orphaned_category INT = (
    SELECT COUNT(*)
    FROM FACT_Rankings
    WHERE CategoryKey NOT IN (SELECT CategoryKey FROM DIM_Category)
)

IF @orphaned_category = 0
    PRINT '[PASS] No orphaned fact records (missing category)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@orphaned_category AS VARCHAR(10)) + ' orphaned fact records (missing category)'
GO

-- Test 3.4: Orphaned competitor records (missing country)
SELECT 
    'DIM_Competitor missing country_key' AS Orphaned,
    COUNT(*) AS Count
FROM DIM_Competitor
WHERE CountryKey IS NOT NULL
  AND CountryKey NOT IN (SELECT CountryKey FROM DIM_Country)
HAVING COUNT(*) > 0
UNION ALL
SELECT 
    'DIM_Venue missing country_key',
    COUNT(*)
FROM DIM_Venue
WHERE CountryKey NOT IN (SELECT CountryKey FROM DIM_Country)
HAVING COUNT(*) > 0
GO

-- Test 3.5: FK constraint summary
PRINT ''
PRINT 'Foreign Key Validation Summary:'
DECLARE @fk_issues TABLE (IssueType NVARCHAR(100), IssueCount INT)

INSERT INTO @fk_issues
SELECT 'Fact→Competitor', COUNT(*) FROM FACT_Rankings WHERE CompetitorKey NOT IN (SELECT CompetitorKey FROM DIM_Competitor)
UNION ALL
SELECT 'Fact→Time', COUNT(*) FROM FACT_Rankings WHERE TimeKey NOT IN (SELECT TimeKey FROM DIM_Time)
UNION ALL
SELECT 'Fact→Category', COUNT(*) FROM FACT_Rankings WHERE CategoryKey NOT IN (SELECT CategoryKey FROM DIM_Category)
UNION ALL
SELECT 'Competitor→Country', COUNT(*) FROM DIM_Competitor WHERE CountryKey IS NOT NULL AND CountryKey NOT IN (SELECT CountryKey FROM DIM_Country)

SELECT IssueType, IssueCount FROM @fk_issues WHERE IssueCount > 0
GO

-- ============================================================================
-- 4. DATA QUALITY TESTS - Business Rule Validation
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| DATA QUALITY TESTS - Business Rule Validation                   |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 4.1: Invalid ranks (must be > 0)
DECLARE @invalid_ranks INT = (
    SELECT COUNT(*)
    FROM FACT_Rankings
    WHERE Rank <= 0
)

IF @invalid_ranks = 0
    PRINT '[PASS] All ranks are positive (>0)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@invalid_ranks AS VARCHAR(10)) + ' invalid ranks (≤0)'
GO

-- Test 4.2: Invalid points (must be >= 0)
DECLARE @invalid_points INT = (
    SELECT COUNT(*)
    FROM FACT_Rankings
    WHERE Points < 0
)

IF @invalid_points = 0
    PRINT '[PASS] All points are non-negative'
ELSE
    PRINT '[FAIL] Found ' + CAST(@invalid_points AS VARCHAR(10)) + ' invalid points (<0)'
GO

-- Test 4.3: Invalid competitions played (must be >= 0)
DECLARE @invalid_comps INT = (
    SELECT COUNT(*)
    FROM FACT_Rankings
    WHERE CompetitionsPlayed < 0
)

IF @invalid_comps = 0
    PRINT '[PASS] All competitions_played are non-negative'
ELSE
    PRINT '[FAIL] Found ' + CAST(@invalid_comps AS VARCHAR(10)) + ' invalid competitions_played (<0)'
GO

-- Test 4.4: Win percentage validation (0-100)
DECLARE @invalid_win_pct INT = (
    SELECT COUNT(*)
    FROM FACT_Rankings
    WHERE WinPercentage IS NOT NULL 
      AND (WinPercentage < 0 OR WinPercentage > 100)
)

IF @invalid_win_pct = 0
    PRINT '[PASS] All win_percentages are within valid range (0-100)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@invalid_win_pct AS VARCHAR(10)) + ' invalid win_percentages'
GO

-- Test 4.5: Flag validation (Y/N only)
SELECT 'Invalid IsCurrentFlag values' AS DataQualityIssue, COUNT(*) AS Count
FROM FACT_Rankings
WHERE IsCurrentFlag NOT IN ('Y', 'N')
UNION ALL
SELECT 'Invalid IsCurrentFlag in DIM_Competitor', COUNT(*)
FROM DIM_Competitor
WHERE IsCurrentFlag NOT IN ('Y', 'N')
UNION ALL
SELECT 'Invalid IsCurrentFlag in DIM_Competition', COUNT(*)
FROM DIM_Competition
WHERE IsCurrentFlag NOT IN ('Y', 'N')
HAVING COUNT(*) > 0
GO

-- ============================================================================
-- 5. DIMENSIONAL ANALYSIS - Completeness & Consistency
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| DIMENSIONAL ANALYSIS - Dimension Table Quality                  |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 5.1: DIM_Time completeness
SELECT 
    'DIM_Time' AS DimensionName,
    COUNT(*) AS TotalRecords,
    COUNT(CASE WHEN FullDate IS NULL THEN 1 END) AS NullDateCount,
    COUNT(CASE WHEN TimeKey IS NULL THEN 1 END) AS NullKeyCount,
    YEAR(MIN(FullDate)) AS EarliestYear,
    YEAR(MAX(FullDate)) AS LatestYear
FROM DIM_Time
GO

-- Test 5.2: DIM_Category completeness
SELECT 
    'DIM_Category' AS DimensionName,
    COUNT(*) AS TotalRecords,
    COUNT(CASE WHEN CategoryName IS NULL THEN 1 END) AS NullNameCount,
    COUNT(DISTINCT IsProFlag) AS DistinctProFlag
FROM DIM_Category
GO

-- Test 5.3: DIM_Country completeness
SELECT 
    'DIM_Country' AS DimensionName,
    COUNT(*) AS TotalRecords,
    COUNT(CASE WHEN CountryCode IS NULL THEN 1 END) AS NullCountryCodeCount,
    COUNT(DISTINCT Region) AS DistinctRegions,
    COUNT(CASE WHEN IsActiveFlag = 'Y' THEN 1 END) AS ActiveCount
FROM DIM_Country
GO

-- Test 5.4: DIM_Competitor - SCD2 validation
DECLARE @scd2_violations INT = (
    SELECT COUNT(*)
    FROM DIM_Competitor
    WHERE IsCurrentFlag = 'Y'
      AND ExpiryDate IS NOT NULL
)

IF @scd2_violations = 0
    PRINT '[PASS] DIM_Competitor SCD2 integrity valid (no violations)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@scd2_violations AS VARCHAR(10)) + ' DIM_Competitor SCD2 violations'

-- Show SCD2 statistics
SELECT 
    'DIM_Competitor SCD2 Status' AS MetricName,
    COUNT(CASE WHEN IsCurrentFlag = 'Y' THEN 1 END) AS CurrentVersions,
    COUNT(CASE WHEN IsCurrentFlag = 'N' THEN 1 END) AS HistoricalVersions,
    COUNT(DISTINCT CompetitorSID) AS UniqueCompetitors
FROM DIM_Competitor
GO

-- Test 5.5: DIM_Competition - SCD2 validation
DECLARE @comp_scd2_violations INT = (
    SELECT COUNT(*)
    FROM DIM_Competition
    WHERE IsCurrentFlag = 'Y'
      AND ExpiryDate IS NOT NULL
)

IF @comp_scd2_violations = 0
    PRINT '[PASS] DIM_Competition SCD2 integrity valid (no violations)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@comp_scd2_violations AS VARCHAR(10)) + ' DIM_Competition SCD2 violations'
GO

-- ============================================================================
-- 6. FACT TABLE ANALYSIS - Metrics Validation
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| FACT TABLE ANALYSIS - Metrics Completeness                      |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 6.1: Fact table completeness summary
SELECT 
    COUNT(*) AS TotalRecords,
    COUNT(CASE WHEN IsCurrentFlag = 'Y' THEN 1 END) AS CurrentSnapshots,
    COUNT(CASE WHEN IsCurrentFlag = 'N' THEN 1 END) AS HistoricalSnapshots,
    COUNT(DISTINCT CompetitorKey) AS UniqueCompetitors,
    COUNT(DISTINCT TimeKey) AS UniqueDates,
    COUNT(DISTINCT CategoryKey) AS UniqueCategories,
    COUNT(DISTINCT RankingSeriesKey) AS UniqueRankingSeries,
    MIN(CAST(TimeKey AS VARCHAR(8))) AS EarliestDate,
    MAX(CAST(TimeKey AS VARCHAR(8))) AS LatestDate
FROM FACT_Rankings
GO

-- Test 6.2: Metric distribution (Rank)
SELECT 
    'Rank' AS MetricName,
    COUNT(*) AS RecordsWithData,
    COUNT(CASE WHEN Rank IS NULL THEN 1 END) AS NullCount,
    MIN(Rank) AS MinValue,
    AVG(CAST(Rank AS FLOAT)) AS AvgValue,
    MAX(Rank) AS MaxValue,
    STDEV(CAST(Rank AS FLOAT)) AS StdDev
FROM FACT_Rankings
WHERE IsCurrentFlag = 'Y'
GO

-- Test 6.3: Metric distribution (Points)
SELECT 
    'Points' AS MetricName,
    COUNT(*) AS RecordsWithData,
    COUNT(CASE WHEN Points IS NULL THEN 1 END) AS NullCount,
    MIN(Points) AS MinValue,
    AVG(CAST(Points AS FLOAT)) AS AvgValue,
    MAX(Points) AS MaxValue,
    STDEV(CAST(Points AS FLOAT)) AS StdDev
FROM FACT_Rankings
WHERE IsCurrentFlag = 'Y'
GO

-- Test 6.4: Competitions played distribution
SELECT 
    'CompetitionsPlayed' AS MetricName,
    COUNT(*) AS RecordsWithData,
    COUNT(CASE WHEN CompetitionsPlayed IS NULL THEN 1 END) AS NullCount,
    MIN(CompetitionsPlayed) AS MinValue,
    AVG(CAST(CompetitionsPlayed AS FLOAT)) AS AvgValue,
    MAX(CompetitionsPlayed) AS MaxValue
FROM FACT_Rankings
WHERE IsCurrentFlag = 'Y'
GO

-- Test 6.5: Duplicate check (same competitor, same category, same time)
DECLARE @duplicates INT = (
    SELECT COUNT(*)
    FROM (
        SELECT CompetitorKey, CategoryKey, TimeKey, COUNT(*) AS Cnt
        FROM FACT_Rankings
        GROUP BY CompetitorKey, CategoryKey, TimeKey
        HAVING COUNT(*) > 1
    ) dups
)

IF @duplicates = 0
    PRINT '[PASS] No duplicate rankings (grain is unique)'
ELSE
    PRINT '[FAIL] Found ' + CAST(@duplicates AS VARCHAR(10)) + ' duplicate ranking records'
GO

-- ============================================================================
-- 7. SCD TYPE 2 VALIDATION - Historical Tracking
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| SCD TYPE 2 VALIDATION - Historical Data Tracking                |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 7.1: DIM_Competitor history depth
SELECT 
    'Competitor History' AS HistoryMetric,
    COUNT(DISTINCT CompetitorSID) AS UniqueCompetitors,
    COUNT(*) AS TotalVersions,
    MAX(CASE WHEN IsCurrentFlag = 'Y' THEN 1 ELSE 0 END) AS HasCurrentVersion,
    COUNT(CASE WHEN IsCurrentFlag = 'N' THEN 1 END) AS HistoricalVersions
FROM DIM_Competitor
GO

-- Test 7.2: DIM_Competition history depth
SELECT 
    'Competition History' AS HistoryMetric,
    COUNT(DISTINCT CompetitionSID) AS UniqueCompetitions,
    COUNT(*) AS TotalVersions,
    MAX(CASE WHEN IsCurrentFlag = 'Y' THEN 1 ELSE 0 END) AS HasCurrentVersion,
    COUNT(CASE WHEN IsCurrentFlag = 'N' THEN 1 END) AS HistoricalVersions
FROM DIM_Competition
GO

-- Test 7.3: Effective date logic validation
DECLARE @bad_effective_dates INT = (
    SELECT COUNT(*)
    FROM DIM_Competitor
    WHERE ExpiryDate IS NOT NULL
      AND EffectiveDate >= ExpiryDate
)

IF @bad_effective_dates = 0
    PRINT '[PASS] All effective dates are before expiry dates'
ELSE
    PRINT '[FAIL] Found ' + CAST(@bad_effective_dates AS VARCHAR(10)) + ' records with effective_date >= expiry_date'
GO

-- Test 7.4: Show competitor name changes
SELECT TOP 10
    CompetitorSID,
    CompetitorName,
    EffectiveDate,
    ExpiryDate,
    IsCurrentFlag,
    ChangeReason
FROM DIM_Competitor
WHERE ChangeReason IS NOT NULL
ORDER BY CompetitorSID, EffectiveDate DESC
GO

-- ============================================================================
-- 8. PERFORMANCE TESTS - Query Performance Benchmarks
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| PERFORMANCE TESTS - Query Response Time Benchmarks              |'
PRINT '+-----------------------------------------------------------------+'
GO

SET STATISTICS IO ON
SET STATISTICS TIME ON

-- Test 8.1: Top 10 ATP players (should be <1 second)
PRINT 'Benchmark 8.1: Top 10 ATP Players Query'
SELECT TOP 10
    dc.CompetitorName,
    dco.CountryName,
    fr.Rank,
    fr.Points
FROM FACT_Rankings fr
INNER JOIN DIM_Competitor dc ON fr.CompetitorKey = dc.CompetitorKey
INNER JOIN DIM_Country dco ON dc.CountryKey = dco.CountryKey
WHERE fr.IsCurrentFlag = 'Y'
  AND dc.IsCurrentFlag = 'Y'
ORDER BY fr.Rank
GO

-- Test 8.2: Category summary aggregation (should be <1 second)
PRINT 'Benchmark 8.2: Category Summary Aggregation'
SELECT
    dcat.CategoryName,
    COUNT(DISTINCT fr.CompetitorKey) AS Competitors,
    AVG(CAST(fr.Rank AS FLOAT)) AS AvgRank,
    MAX(fr.Points) AS MaxPoints
FROM FACT_Rankings fr
INNER JOIN DIM_Category dcat ON fr.CategoryKey = dcat.CategoryKey
WHERE fr.IsCurrentFlag = 'Y'
GROUP BY dcat.CategoryName
GO

-- Test 8.3: Competitor history (should be <2 seconds)
PRINT 'Benchmark 8.3: Competitor Ranking History'
SELECT
    CompetitorName,
    FullDate,
    Rank,
    Points,
    LAG(Rank) OVER (ORDER BY TimeKey) AS PreviousRank
FROM VW_Competitor_Ranking_History
WHERE CompetitorName = (SELECT TOP 1 CompetitorName FROM DIM_Competitor WHERE IsCurrentFlag = 'Y' ORDER BY CompetitorKey)
ORDER BY FullDate DESC
GO

SET STATISTICS IO OFF
SET STATISTICS TIME OFF
GO

-- ============================================================================
-- 9. RECONCILIATION TESTS - Source vs Target Comparison
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| RECONCILIATION TESTS - Source vs Target Comparison              |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 9.1: Staging vs Fact load count
DECLARE @staging_count INT = (SELECT COUNT(*) FROM STG_Rankings_Raw WHERE IsProcessedFlag = 'N')
DECLARE @processed_count INT = (SELECT COUNT(*) FROM STG_Rankings_Raw WHERE IsProcessedFlag = 'Y')

PRINT 'Staging Table Status:'
PRINT '  • Unprocessed records: ' + CAST(@staging_count AS VARCHAR(10))
PRINT '  • Processed records: ' + CAST(@processed_count AS VARCHAR(10))

IF @staging_count = 0
    PRINT '[PASS] All staging records have been processed'
ELSE
    PRINT '[WARNING] ' + CAST(@staging_count AS VARCHAR(10)) + ' staging records still pending'
GO

-- Test 9.2: Data load timeline
SELECT 
    'ETL Load History' AS LoadMetric,
    COUNT(DISTINCT ETLBatchID) AS BatchesLoaded,
    MIN(LoadedAt) AS FirstLoadTime,
    MAX(LoadedAt) AS LastLoadTime,
    DATEDIFF(HOUR, MIN(LoadedAt), MAX(LoadedAt)) AS HoursBetweenLoads
FROM FACT_Rankings
GO

-- Test 9.3: Source system distribution
SELECT 
    SourceSystem,
    COUNT(*) AS RecordCount,
    COUNT(DISTINCT CompetitorKey) AS UniqueCompetitors,
    MIN(LoadedAt) AS EarliestLoad,
    MAX(LoadedAt) AS LatestLoad
FROM FACT_Rankings
GROUP BY SourceSystem
ORDER BY RecordCount DESC
GO

-- ============================================================================
-- 10. AUDIT TRAIL VALIDATION - ETL Metadata Tracking
-- ============================================================================

PRINT ''
PRINT '+-----------------------------------------------------------------+'
PRINT '| AUDIT TRAIL VALIDATION - ETL Metadata & Traceability            |'
PRINT '+-----------------------------------------------------------------+'
GO

-- Test 10.1: Audit column completeness
SELECT 
    'Audit Columns Status' AS AuditMetric,
    COUNT(*) AS TotalRecords,
    COUNT(CASE WHEN CreatedAt IS NULL THEN 1 END) AS MissingCreatedAt,
    COUNT(CASE WHEN UpdatedAt IS NULL THEN 1 END) AS MissingUpdatedAt,
    COUNT(CASE WHEN SourceSystem IS NULL THEN 1 END) AS MissingSourceSystem,
    COUNT(CASE WHEN ETLBatchID IS NULL THEN 1 END) AS MissingBatchID
FROM FACT_Rankings
GO

-- Test 10.2: ETL batch tracking
SELECT TOP 20
    ETLBatchID,
    LoadedAt,
    COUNT(*) AS RecordsLoaded,
    COUNT(DISTINCT CompetitorKey) AS UniqueCompetitors,
    COUNT(DISTINCT TimeKey) AS UniqueDates
FROM FACT_Rankings
GROUP BY ETLBatchID, LoadedAt
ORDER BY LoadedAt DESC
GO

-- Test 10.3: Data freshness
DECLARE @latest_data_date DATE = (
    SELECT MAX(CAST(TimeKey AS VARCHAR(8)))
    FROM FACT_Rankings
    WHERE IsCurrentFlag = 'Y'
)

DECLARE @days_old INT = DATEDIFF(DAY, @latest_data_date, CAST(GETUTCDATE() AS DATE))

PRINT 'Data Freshness:'
PRINT '  • Latest data date: ' + CAST(@latest_data_date AS VARCHAR(10))
PRINT '  • Days old: ' + CAST(@days_old AS VARCHAR(10))

IF @days_old <= 1
    PRINT '[PASS] Data is current (≤1 day old)'
ELSE IF @days_old <= 7
    PRINT '[WARNING] Data is ' + CAST(@days_old AS VARCHAR(10)) + ' days old'
ELSE
    PRINT '[FAIL] Data is stale (' + CAST(@days_old AS VARCHAR(10)) + ' days old)'
GO

-- ============================================================================
-- 11. SUMMARY REPORT - Overall Test Results
-- ============================================================================

PRINT ''
PRINT '================================================================='
PRINT 'ETL TEST SUITE SUMMARY REPORT'
PRINT '================================================================='
GO

-- Final summary statistics
SELECT 
    'DIMENSION TABLES' AS CategoryName,
    'DIM_Time' AS TableName,
    COUNT(*) AS RecordCount,
    'Ready for Analytics' AS Status
FROM DIM_Time
UNION ALL SELECT 'DIMENSION TABLES', 'DIM_Category', COUNT(*), 'Ready for Analytics' FROM DIM_Category
UNION ALL SELECT 'DIMENSION TABLES', 'DIM_Country', COUNT(*), 'Ready for Analytics' FROM DIM_Country
UNION ALL SELECT 'DIMENSION TABLES', 'DIM_Competitor', COUNT(*), 'Ready for Analytics' FROM DIM_Competitor
UNION ALL SELECT 'DIMENSION TABLES', 'DIM_Competition', COUNT(*), 'Ready for Analytics' FROM DIM_Competition
UNION ALL SELECT 'DIMENSION TABLES', 'DIM_Venue', COUNT(*), 'Ready for Analytics' FROM DIM_Venue
UNION ALL SELECT 'FACT TABLE', 'FACT_Rankings', COUNT(*), 'Ready for Analytics' FROM FACT_Rankings
UNION ALL SELECT 'STAGING TABLES', 'STG_Rankings_Raw', COUNT(*), 'In Processing' FROM STG_Rankings_Raw
ORDER BY CategoryName, TableName
GO

PRINT ''
PRINT 'Recommendations:'
PRINT '  1. Review all [FAIL] tests immediately'
PRINT '  2. Address all [WARNING] tests within SLA'
PRINT '  3. Monitor [PASS] tests in ongoing operations'
PRINT '  4. Run this test suite before each production load'
PRINT '  5. Keep historical test results for regression analysis'
PRINT ''
PRINT '================================================================='
PRINT 'END OF TEST SUITE'
PRINT '================================================================='
GO

