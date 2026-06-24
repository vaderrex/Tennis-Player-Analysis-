-- ============================================================================
-- Tennis Rankings Star Schema - SQL Server DDL
-- Target: SQL Server 2019+ (SSMS 22+)
-- Optimized for: Analytics & Reporting
-- Date Generated: 2026-06-02
-- ============================================================================
-- This script creates a complete star schema data warehouse for tennis rankings
-- with production-grade indexes, constraints, and stored procedures.
--
-- EXECUTION STEPS:
-- 1. Update USE [DatabaseName] to your target database
-- 2. Open in SSMS
-- 3. Press F5 to execute
-- 4. Monitor messages tab for completion
-- ============================================================================

USE [TennisRankings]
GO

-- ============================================================================
-- SECTION 1: CREATE DIMENSION TABLES
-- ============================================================================

PRINT '========== CREATING DIMENSION TABLES ==========='
GO

-- DIM_TIME: Standard calendar dimension (pre-populate with 20+ years)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'DIM_Time')
BEGIN
    CREATE TABLE [dbo].[DIM_Time] (
        [TimeKey] INT PRIMARY KEY,                    -- YYYYMMDD format
        [FullDate] DATE NOT NULL UNIQUE,
        [Year] INT NOT NULL,
        [Quarter] INT NOT NULL,
        [Month] INT NOT NULL,
        [Week] INT NOT NULL,
        [Day] INT NOT NULL,
        [DayOfWeek] INT NOT NULL,                     -- 1=Monday, 7=Sunday (ISO)
        [DayName] VARCHAR(10) NOT NULL,
        [IsWeekend] CHAR(1) NOT NULL,                 -- Y/N
        [WeekStartDate] DATE NOT NULL,
        [MonthStartDate] DATE NOT NULL,
        [QuarterStartDate] DATE NOT NULL,
        [YearStartDate] DATE NOT NULL,
        [FiscalYear] INT,
        [Season] VARCHAR(20),                         -- "2025-26 ATP"
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [SourceSystem] VARCHAR(64) NOT NULL DEFAULT 'SYSTEM',
        
        CONSTRAINT [CK_Time_Quarter] CHECK ([Quarter] BETWEEN 1 AND 4),
        CONSTRAINT [CK_Time_Month] CHECK ([Month] BETWEEN 1 AND 12),
        CONSTRAINT [CK_Time_Week] CHECK ([Week] BETWEEN 1 AND 53),
        CONSTRAINT [CK_Time_Day] CHECK ([Day] BETWEEN 1 AND 31),
        CONSTRAINT [CK_Time_DayOfWeek] CHECK ([DayOfWeek] BETWEEN 1 AND 7)
    );
    
    CREATE NONCLUSTERED INDEX [IX_DIM_Time_FullDate] ON [dbo].[DIM_Time]([FullDate]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Time_YearMonth] ON [dbo].[DIM_Time]([Year], [Month]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Time_Season] ON [dbo].[DIM_Time]([Season]);
    
    PRINT '✅ DIM_Time table created'
END
GO

-- DIM_CATEGORY: Tennis categories (ATP, WTA, Challenger, ITF)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'DIM_Category')
BEGIN
    CREATE TABLE [dbo].[DIM_Category] (
        [CategoryKey] INT PRIMARY KEY,
        [CategorySID] VARCHAR(64) NOT NULL UNIQUE,    -- Source: sr:category:X
        [CategoryName] VARCHAR(255) NOT NULL,
        [CategoryDescription] NVARCHAR(MAX),
        [IsProFlag] CHAR(1) NOT NULL DEFAULT 'Y',
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [SourceSystem] VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
        
        CONSTRAINT [CK_Category_IsProFlag] CHECK ([IsProFlag] IN ('Y', 'N'))
    );
    
    CREATE NONCLUSTERED INDEX [IX_DIM_Category_Name] ON [dbo].[DIM_Category]([CategoryName]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Category_SID] ON [dbo].[DIM_Category]([CategorySID]);
    
    PRINT '✅ DIM_Category table created'
END
GO

-- DIM_COUNTRY: Geographic dimension
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'DIM_Country')
BEGIN
    CREATE TABLE [dbo].[DIM_Country] (
        [CountryKey] INT PRIMARY KEY,
        [CountryCode] VARCHAR(16) NOT NULL UNIQUE,    -- ISO-3166-1-alpha-3/other
        [CountryName] VARCHAR(255) NOT NULL,
        [Region] VARCHAR(100),                        -- Continent
        [SubRegion] VARCHAR(100),
        [IsActiveFlag] CHAR(1) NOT NULL DEFAULT 'Y',
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [SourceSystem] VARCHAR(64) NOT NULL DEFAULT 'GEO_DB',
        
        CONSTRAINT [CK_Country_IsActive] CHECK ([IsActiveFlag] IN ('Y', 'N'))
    );
    
    CREATE NONCLUSTERED INDEX [IX_DIM_Country_Name] ON [dbo].[DIM_Country]([CountryName]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Country_Region] ON [dbo].[DIM_Country]([Region]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Country_Code] ON [dbo].[DIM_Country]([CountryCode]);
    
    PRINT '✅ DIM_Country table created'
END
GO

-- DIM_VENUE: Tennis venues and courts
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'DIM_Venue')
BEGIN
    CREATE TABLE [dbo].[DIM_Venue] (
        [VenueKey] INT PRIMARY KEY,
        [VenueSID] VARCHAR(64) NOT NULL UNIQUE,       -- Source: sr:venue:X
        [VenueName] VARCHAR(255) NOT NULL,
        [CountryKey] INT NOT NULL,
        [City] VARCHAR(255),
        [Timezone] VARCHAR(128),
        [Capacity] INT,
        [Surface] VARCHAR(50),                        -- Clay, Grass, Hard, Carpet
        [ComplexName] VARCHAR(255),
        [Latitude] DECIMAL(10, 8),
        [Longitude] DECIMAL(11, 8),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [SourceSystem] VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
        
        CONSTRAINT [FK_Venue_Country] FOREIGN KEY ([CountryKey]) 
            REFERENCES [dbo].[DIM_Country]([CountryKey]),
        CONSTRAINT [CK_Venue_Surface] CHECK ([Surface] IN ('Clay', 'Grass', 'Hard', 'Carpet', NULL))
    );
    
    CREATE NONCLUSTERED INDEX [IX_DIM_Venue_Name] ON [dbo].[DIM_Venue]([VenueName]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Venue_Country] ON [dbo].[DIM_Venue]([CountryKey]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Venue_City] ON [dbo].[DIM_Venue]([City]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Venue_SID] ON [dbo].[DIM_Venue]([VenueSID]);
    
    PRINT '✅ DIM_Venue table created'
END
GO

-- DIM_RANKING_SERIES: Reference to ranking systems
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'DIM_RankingSeries')
BEGIN
    CREATE TABLE [dbo].[DIM_RankingSeries] (
        [RankingSeriesKey] INT IDENTITY(1,1) PRIMARY KEY,   -- Auto Incrementation
        [SeriesSID] VARCHAR(64) NOT NULL UNIQUE,
        [SeriesName] VARCHAR(255) NOT NULL,
        [SeriesDescription] NVARCHAR(MAX),
        [SeriesType] VARCHAR(50),                     -- Current, Historical, Projected
        [SourceSystem] VARCHAR(64) NOT NULL,
        [IsActiveFlag] CHAR(1) NOT NULL DEFAULT 'Y',
        [EffectiveDate] DATE NOT NULL,
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        
        CONSTRAINT [CK_RankingSeries_Type] CHECK ([SeriesType] IN ('Current', 'Historical', 'Projected')),
        CONSTRAINT [CK_RankingSeries_Active] CHECK ([IsActiveFlag] IN ('Y', 'N'))
    );
    
    CREATE NONCLUSTERED INDEX [IX_DIM_RankingSeries_Name] ON [dbo].[DIM_RankingSeries]([SeriesName]);
    CREATE NONCLUSTERED INDEX [IX_DIM_RankingSeries_Active] ON [dbo].[DIM_RankingSeries]([IsActiveFlag]);
    
    PRINT '✅ DIM_RankingSeries table created'
END
GO

-- DIM_COMPETITOR: Players/teams (SCD Type 2 - with history tracking)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'DIM_Competitor')
BEGIN
    CREATE TABLE [dbo].[DIM_Competitor] (
        [CompetitorKey] BIGINT PRIMARY KEY,           -- Surrogate key (MD5-based)
        [CompetitorSID] VARCHAR(64) NOT NULL,         -- Source: sr:competitor:X
        [CompetitorName] VARCHAR(255) NOT NULL,
        [CountryKey] INT,
        [CountryCode] VARCHAR(16),
        [Abbreviation] VARCHAR(64),
        [CompetitorType] VARCHAR(50),                 -- Individual, Team, Doubles
        [CompetitionSpecialty] VARCHAR(50),           -- Singles, Doubles, Mixed
        
        -- SCD Type 2 Tracking Columns
        [EffectiveDate] DATE NOT NULL,
        [ExpiryDate] DATE,                            -- NULL = current version
        [IsCurrentFlag] CHAR(1) NOT NULL DEFAULT 'Y',
        [ChangeReason] VARCHAR(255),
        
        -- Audit Columns
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [SourceSystem] VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
        [SourceRecordID] VARCHAR(128),
        [ETLBatchID] VARCHAR(128),
        
        CONSTRAINT [FK_Competitor_Country] FOREIGN KEY ([CountryKey]) 
            REFERENCES [dbo].[DIM_Country]([CountryKey]),
        CONSTRAINT [CK_Competitor_Type] CHECK ([CompetitorType] IN ('Individual', 'Team', 'Doubles', NULL)),
        CONSTRAINT [CK_Competitor_Specialty] CHECK ([CompetitionSpecialty] IN ('Singles', 'Doubles', 'Mixed', NULL)),
        CONSTRAINT [CK_Competitor_IsCurrentFlag] CHECK ([IsCurrentFlag] IN ('Y', 'N')),
        CONSTRAINT [CK_Competitor_SCD2] CHECK (
            ([IsCurrentFlag] = 'Y' AND [ExpiryDate] IS NULL) OR
            ([IsCurrentFlag] = 'N' AND [ExpiryDate] IS NOT NULL)
        )
    );
    
    CREATE NONCLUSTERED INDEX [IX_DIM_Competitor_SID] ON [dbo].[DIM_Competitor]([CompetitorSID]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competitor_Name] ON [dbo].[DIM_Competitor]([CompetitorName]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competitor_Current] ON [dbo].[DIM_Competitor]([IsCurrentFlag], [EffectiveDate] DESC);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competitor_SCD] ON [dbo].[DIM_Competitor]([CompetitorSID], [EffectiveDate] DESC);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competitor_Country] ON [dbo].[DIM_Competitor]([CountryKey]);
    
    PRINT '✅ DIM_Competitor table created'
END
GO

-- DIM_COMPETITION: Tournaments and events (SCD Type 2)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'DIM_Competition')
BEGIN
    CREATE TABLE [dbo].[DIM_Competition] (
        [CompetitionKey] BIGINT PRIMARY KEY,
        [CompetitionSID] VARCHAR(64) NOT NULL,        -- Source: sr:competition:X
        [CompetitionName] VARCHAR(255) NOT NULL,
        [CompetitionType] VARCHAR(50),                -- Singles, Doubles, Mixed
        [Gender] VARCHAR(50),                         -- Men, Women, Mixed
        [Level] VARCHAR(100),                         -- Grand Slam, ATP500, etc.
        [CategoryKey] INT NOT NULL,
        [ParentCompetitionKey] BIGINT,                -- Self-join hierarchy
        [IsTeamCompetitionFlag] CHAR(1) NOT NULL DEFAULT 'N',
        
        -- SCD Type 2 Tracking
        [EffectiveDate] DATE NOT NULL,
        [ExpiryDate] DATE,
        [IsCurrentFlag] CHAR(1) NOT NULL DEFAULT 'Y',
        [ChangeReason] VARCHAR(255),
        
        -- Audit
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [SourceSystem] VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
        [SourceRecordID] VARCHAR(128),
        
        CONSTRAINT [FK_Competition_Category] FOREIGN KEY ([CategoryKey]) 
            REFERENCES [dbo].[DIM_Category]([CategoryKey]),
        CONSTRAINT [FK_Competition_Parent] FOREIGN KEY ([ParentCompetitionKey]) 
            REFERENCES [dbo].[DIM_Competition]([CompetitionKey]),
        CONSTRAINT [CK_Competition_Type] CHECK ([CompetitionType] IN ('Singles', 'Doubles', 'Mixed', NULL)),
        CONSTRAINT [CK_Competition_Gender] CHECK ([Gender] IN ('Men', 'Women', 'Mixed', NULL)),
        CONSTRAINT [CK_Competition_TeamFlag] CHECK ([IsTeamCompetitionFlag] IN ('Y', 'N')),
        CONSTRAINT [CK_Competition_CurrentFlag] CHECK ([IsCurrentFlag] IN ('Y', 'N')),
        CONSTRAINT [CK_Competition_SCD2] CHECK (
            ([IsCurrentFlag] = 'Y' AND [ExpiryDate] IS NULL) OR
            ([IsCurrentFlag] = 'N' AND [ExpiryDate] IS NOT NULL)
        )
    );
    
    CREATE NONCLUSTERED INDEX [IX_DIM_Competition_SID] ON [dbo].[DIM_Competition]([CompetitionSID]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competition_Name] ON [dbo].[DIM_Competition]([CompetitionName]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competition_Level] ON [dbo].[DIM_Competition]([Level]);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competition_Current] ON [dbo].[DIM_Competition]([IsCurrentFlag], [EffectiveDate] DESC);
    CREATE NONCLUSTERED INDEX [IX_DIM_Competition_Category] ON [dbo].[DIM_Competition]([CategoryKey]);
    
    PRINT '✅ DIM_Competition table created'
END
GO

-- ============================================================================
-- SECTION 2: CREATE FACT TABLE
-- ============================================================================

PRINT '========== CREATING FACT TABLE ==========='
GO

-- FACT_RANKINGS: Core fact table (grain: one row per competitor per snapshot)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'FACT_Rankings')
BEGIN
    CREATE TABLE [dbo].[FACT_Rankings] (
        [RankingFactKey] BIGINT PRIMARY KEY IDENTITY(1, 1),  -- Auto-increment
        [CompetitorKey] BIGINT NOT NULL,
        [RankingSeriesKey] INT NOT NULL,
        [TimeKey] INT NOT NULL,
        [CategoryKey] INT NOT NULL,
        [CompetitionKey] BIGINT,
        [VenueKey] INT,
        
        -- Metrics (Measures)
        [Rank] BIGINT NOT NULL,
        [Points] BIGINT,
        [CompetitionsPlayed] BIGINT,
        [RankMovement] INT,                          -- Positive = gained places
        [Wins] BIGINT,
        [Losses] BIGINT,
        [WinPercentage] DECIMAL(10, 4),              -- 0.0000 to 100.0000
        
        -- Additive Flag
        [IsAdditiveFlag] CHAR(1) NOT NULL DEFAULT 'N',  -- Most measures semi-additive
        
        -- Audit & Metadata
        [IsCurrentFlag] CHAR(1) NOT NULL DEFAULT 'Y',
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [SourceSystem] VARCHAR(64) NOT NULL DEFAULT 'SportRadar',
        [SourceRecordID] VARCHAR(128),
        [ExtractedAt] DATETIME2,
        [LoadedAt] DATETIME2,
        [ETLBatchID] VARCHAR(128),
        
        -- Foreign Keys & Constraints
        CONSTRAINT [FK_Rankings_Competitor] FOREIGN KEY ([CompetitorKey]) 
            REFERENCES [dbo].[DIM_Competitor]([CompetitorKey]),
        CONSTRAINT [FK_Rankings_RankingSeries] FOREIGN KEY ([RankingSeriesKey]) 
            REFERENCES [dbo].[DIM_RankingSeries]([RankingSeriesKey]),
        CONSTRAINT [FK_Rankings_Time] FOREIGN KEY ([TimeKey]) 
            REFERENCES [dbo].[DIM_Time]([TimeKey]),
        CONSTRAINT [FK_Rankings_Category] FOREIGN KEY ([CategoryKey]) 
            REFERENCES [dbo].[DIM_Category]([CategoryKey]),
        CONSTRAINT [FK_Rankings_Competition] FOREIGN KEY ([CompetitionKey]) 
            REFERENCES [dbo].[DIM_Competition]([CompetitionKey]),
        CONSTRAINT [FK_Rankings_Venue] FOREIGN KEY ([VenueKey]) 
            REFERENCES [dbo].[DIM_Venue]([VenueKey]),
        
        -- Data Quality Constraints
        CONSTRAINT [CK_Rankings_Rank] CHECK ([Rank] > 0),
        CONSTRAINT [CK_Rankings_Points] CHECK ([Points] >= 0 OR [Points] IS NULL),
        CONSTRAINT [CK_Rankings_CompetitionsPlayed] CHECK ([CompetitionsPlayed] >= 0 OR [CompetitionsPlayed] IS NULL),
        CONSTRAINT [CK_Rankings_WinPct] CHECK ([WinPercentage] >= 0 AND [WinPercentage] <= 100 OR [WinPercentage] IS NULL),
        CONSTRAINT [CK_Rankings_IsCurrentFlag] CHECK ([IsCurrentFlag] IN ('Y', 'N')),
        CONSTRAINT [CK_Rankings_IsAdditiveFlag] CHECK ([IsAdditiveFlag] IN ('Y', 'N'))
    );
    
    -- Indexes optimized for typical reporting queries
    CREATE NONCLUSTERED INDEX [IX_FACT_Rankings_Competitor_Time] 
        ON [dbo].[FACT_Rankings]([CompetitorKey], [TimeKey]);
    
    CREATE NONCLUSTERED INDEX [IX_FACT_Rankings_Category_Time] 
        ON [dbo].[FACT_Rankings]([CategoryKey], [TimeKey]);
    
    CREATE NONCLUSTERED INDEX [IX_FACT_Rankings_Time] 
        ON [dbo].[FACT_Rankings]([TimeKey])
        INCLUDE ([Rank], [Points], [CompetitorKey]);
    
    CREATE NONCLUSTERED INDEX [IX_FACT_Rankings_RankingSeries] 
        ON [dbo].[FACT_Rankings]([RankingSeriesKey], [TimeKey]);
    
    CREATE NONCLUSTERED INDEX [IX_FACT_Rankings_Current] 
        ON [dbo].[FACT_Rankings]([IsCurrentFlag])
        WHERE [IsCurrentFlag] = 'Y';
    
    CREATE NONCLUSTERED INDEX [IX_FACT_Rankings_Points_Desc] 
        ON [dbo].[FACT_Rankings]([Points] DESC)
        WHERE [IsCurrentFlag] = 'Y';
    
    CREATE NONCLUSTERED INDEX [IX_FACT_Rankings_Batch] 
        ON [dbo].[FACT_Rankings]([ETLBatchID], [LoadedAt]);
    
    PRINT '✅ FACT_Rankings table created'
END
GO

-- ============================================================================
-- SECTION 3: CREATE BRIDGE TABLES (Optional - for M:M relationships)
-- ============================================================================

PRINT '========== CREATING BRIDGE TABLES ==========='
GO

-- BRIDGE_Competitor_Competition: Connects competitors to competitions
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'BRIDGE_Competitor_Competition')
BEGIN
    CREATE TABLE [dbo].[BRIDGE_Competitor_Competition] (
        [BridgeKey] BIGINT PRIMARY KEY IDENTITY(1, 1),
        [CompetitorKey] BIGINT NOT NULL,
        [CompetitionKey] BIGINT NOT NULL,
        [ParticipationType] VARCHAR(50),              -- Participant, Winner, Runner-up
        [AppearedDate] DATE,
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        
        CONSTRAINT [FK_Bridge_Competitor] FOREIGN KEY ([CompetitorKey]) 
            REFERENCES [dbo].[DIM_Competitor]([CompetitorKey]),
        CONSTRAINT [FK_Bridge_Competition] FOREIGN KEY ([CompetitionKey]) 
            REFERENCES [dbo].[DIM_Competition]([CompetitionKey]),
        CONSTRAINT [UQ_Bridge_Competitor_Competition] UNIQUE ([CompetitorKey], [CompetitionKey])
    );
    
    CREATE NONCLUSTERED INDEX [IX_BRIDGE_Competitor] ON [dbo].[BRIDGE_Competitor_Competition]([CompetitorKey]);
    CREATE NONCLUSTERED INDEX [IX_BRIDGE_Competition] ON [dbo].[BRIDGE_Competitor_Competition]([CompetitionKey]);
    
    PRINT '✅ BRIDGE_Competitor_Competition table created'
END
GO

-- ============================================================================
-- SECTION 4: CREATE STAGING TABLES (ETL Processing)
-- ============================================================================

PRINT '========== CREATING STAGING TABLES ==========='
GO

-- STG_Rankings_Raw: Temporary staging for incoming rankings data
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'STG_Rankings_Raw')
BEGIN
    CREATE TABLE [dbo].[STG_Rankings_Raw] (
        [StgKey] BIGINT PRIMARY KEY IDENTITY(1, 1),
        [CompetitorSID] VARCHAR(64),
        [CompetitorName] VARCHAR(255),
        [CategorySID] VARCHAR(64),
        [Rank] BIGINT,
        [Points] BIGINT,
        [Movement] INT,
        [CompetitionsPlayed] BIGINT,
        [RankingDate] DATE,
        [SourceSystem] VARCHAR(64),
        [ExtractedAt] DATETIME2,
        [LoadedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [IsProcessedFlag] CHAR(1) DEFAULT 'N',
        
        CONSTRAINT [CK_STG_Processed] CHECK ([IsProcessedFlag] IN ('Y', 'N'))
    );
    
    CREATE NONCLUSTERED INDEX [IX_STG_Rankings_Processed] ON [dbo].[STG_Rankings_Raw]([IsProcessedFlag]);
    CREATE NONCLUSTERED INDEX [IX_STG_Rankings_Date] ON [dbo].[STG_Rankings_Raw]([RankingDate]);
    CREATE NONCLUSTERED INDEX [IX_STG_Rankings_Category] ON [dbo].[STG_Rankings_Raw]([CategorySID]);
    
    PRINT '✅ STG_Rankings_Raw table created'
END
GO

-- STG_Competitor_Changes: Track dimension changes for SCD Type 2
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'STG_Competitor_Changes')
BEGIN
    CREATE TABLE [dbo].[STG_Competitor_Changes] (
        [StgKey] BIGINT PRIMARY KEY IDENTITY(1, 1),
        [CompetitorSID] VARCHAR(64),
        [PreviousName] VARCHAR(255),
        [NewName] VARCHAR(255),
        [ChangeType] VARCHAR(50),                     -- UPDATE, INSERT, DELETE
        [ChangeDate] DATETIME2 DEFAULT GETUTCDATE()
    );
    
    CREATE NONCLUSTERED INDEX [IX_STG_Competitor_Changes_Date] ON [dbo].[STG_Competitor_Changes]([ChangeDate]);
    
    PRINT '✅ STG_Competitor_Changes table created'
END
GO

-- ============================================================================
-- SECTION 5: CREATE DATA QUALITY AND AUDIT VIEWS
-- ============================================================================

PRINT '========== CREATING REPORTING VIEWS ==========='
GO

-- VIEW: Current Rankings (latest snapshot)
IF EXISTS (SELECT 1 FROM sys.views WHERE name = 'VW_CurrentRankings')
BEGIN
    DROP VIEW [dbo].[VW_CurrentRankings]
END
GO

CREATE VIEW [dbo].[VW_CurrentRankings]
AS
SELECT
    dc.[CompetitorName],
    dco.[CountryName],
    dcat.[CategoryName],
    fr.[Rank],
    fr.[Points],
    fr.[CompetitionsPlayed],
    fr.[RankMovement],
    fr.[WinPercentage],
    dt.[FullDate] AS [RankingDate],
    drs.[SeriesName] AS [RankingSeriesName]
FROM [dbo].[FACT_Rankings] fr
INNER JOIN [dbo].[DIM_Competitor] dc ON fr.[CompetitorKey] = dc.[CompetitorKey]
INNER JOIN [dbo].[DIM_Country] dco ON dc.[CountryKey] = dco.[CountryKey]
INNER JOIN [dbo].[DIM_Category] dcat ON fr.[CategoryKey] = dcat.[CategoryKey]
INNER JOIN [dbo].[DIM_Time] dt ON fr.[TimeKey] = dt.[TimeKey]
INNER JOIN [dbo].[DIM_RankingSeries] drs ON fr.[RankingSeriesKey] = drs.[RankingSeriesKey]
WHERE fr.[IsCurrentFlag] = 'Y'
  AND dc.[IsCurrentFlag] = 'Y';

GO

PRINT '✅ VW_CurrentRankings view created'
GO

-- VIEW: Competitor Ranking History (time-series)
IF EXISTS (SELECT 1 FROM sys.views WHERE name = 'VW_Competitor_Ranking_History')
BEGIN
    DROP VIEW [dbo].[VW_Competitor_Ranking_History]
END
GO

CREATE VIEW [dbo].[VW_Competitor_Ranking_History]
AS
SELECT
    dc.[CompetitorName],
    dco.[CountryName],
    dcat.[CategoryName],
    dt.[FullDate],
    fr.[Rank],
    fr.[Points],
    fr.[RankMovement],
    LAG(fr.[Rank]) OVER (
        PARTITION BY dc.[CompetitorKey], dcat.[CategoryKey]
        ORDER BY dt.[TimeKey]
    ) AS [PreviousRank],
    LEAD(fr.[Rank]) OVER (
        PARTITION BY dc.[CompetitorKey], dcat.[CategoryKey]
        ORDER BY dt.[TimeKey]
    ) AS [NextRank]
FROM [dbo].[FACT_Rankings] fr
INNER JOIN [dbo].[DIM_Competitor] dc ON fr.[CompetitorKey] = dc.[CompetitorKey]
INNER JOIN [dbo].[DIM_Country] dco ON dc.[CountryKey] = dco.[CountryKey]
INNER JOIN [dbo].[DIM_Category] dcat ON fr.[CategoryKey] = dcat.[CategoryKey]
INNER JOIN [dbo].[DIM_Time] dt ON fr.[TimeKey] = dt.[TimeKey]
WHERE dc.[IsCurrentFlag] = 'Y';

GO

PRINT '✅ VW_Competitor_Ranking_History view created'
GO

-- VIEW: Data Quality Checks
IF EXISTS (SELECT 1 FROM sys.views WHERE name = 'VW_Data_Quality_Checks')
BEGIN
    DROP VIEW [dbo].[VW_Data_Quality_Checks]
END
GO

CREATE VIEW [dbo].[VW_Data_Quality_Checks]
AS
SELECT 'FACT_Rankings' AS [TableName], 'Missing Dimensions' AS [CheckType], COUNT(*) AS [IssueCount]
FROM [dbo].[FACT_Rankings]
WHERE [CompetitorKey] IS NULL
   OR [RankingSeriesKey] IS NULL
   OR [TimeKey] IS NULL

UNION ALL

SELECT 'FACT_Rankings', 'Invalid Rank (Zero or Negative)', COUNT(*)
FROM [dbo].[FACT_Rankings]
WHERE [Rank] <= 0

UNION ALL

SELECT 'FACT_Rankings', 'Negative Points', COUNT(*)
FROM [dbo].[FACT_Rankings]
WHERE [Points] < 0

UNION ALL

SELECT 'DIM_Competitor', 'SCD Type 2 Violation', COUNT(*)
FROM [dbo].[DIM_Competitor]
WHERE [IsCurrentFlag] = 'Y'
  AND [ExpiryDate] IS NOT NULL

UNION ALL

SELECT 'DIM_Competition', 'SCD Type 2 Violation', COUNT(*)
FROM [dbo].[DIM_Competition]
WHERE [IsCurrentFlag] = 'Y'
  AND [ExpiryDate] IS NOT NULL;

GO

PRINT '✅ VW_Data_Quality_Checks view created'
GO

-- VIEW: Category Performance Summary
IF EXISTS (SELECT 1 FROM sys.views WHERE name = 'VW_Category_Performance')
BEGIN
    DROP VIEW [dbo].[VW_Category_Performance]
END
GO

CREATE VIEW [dbo].[VW_Category_Performance]
AS
SELECT
    dcat.[CategoryName],
    dt.[FullDate],
    COUNT(DISTINCT fr.[CompetitorKey]) AS [TotalCompetitors],
    AVG(CAST(fr.[Rank] AS FLOAT)) AS [AvgRank],
    MAX(fr.[Points]) AS [MaxPoints],
    MIN(fr.[Points]) AS [MinPoints],
    SUM(fr.[CompetitionsPlayed]) AS [TotalCompetitionsPlayed]
FROM [dbo].[FACT_Rankings] fr
INNER JOIN [dbo].[DIM_Category] dcat ON fr.[CategoryKey] = dcat.[CategoryKey]
INNER JOIN [dbo].[DIM_Time] dt ON fr.[TimeKey] = dt.[TimeKey]
WHERE fr.[IsCurrentFlag] = 'Y'
GROUP BY dcat.[CategoryName], dt.[FullDate], dcat.[CategoryKey], dt.[TimeKey];

GO

PRINT '✅ VW_Category_Performance view created'
GO

-- ============================================================================
-- SECTION 6: CREATE STORED PROCEDURES
-- ============================================================================

PRINT '========== CREATING STORED PROCEDURES ==========='
GO

-- STORED PROCEDURE: Load rankings from staging
IF EXISTS (SELECT 1 FROM sys.procedures WHERE name = 'SP_Load_Rankings_From_Staging')
BEGIN
    DROP PROCEDURE [dbo].[SP_Load_Rankings_From_Staging]
END
GO

CREATE PROCEDURE [dbo].[SP_Load_Rankings_From_Staging]
    @p_BatchID VARCHAR(128),
    @p_RankingDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @v_TimeKey INT;
    DECLARE @v_RankingSeriesKey INT;
    DECLARE @v_RowsInserted BIGINT = 0;
    DECLARE @v_RowsUpdated BIGINT = 0;
    
    BEGIN TRY
        -- Step 1: Get time key
        SET @v_TimeKey = CAST(FORMAT(@p_RankingDate, 'yyyyMMdd') AS INT);
        
        -- Step 2: Ensure time dimension exists
        IF NOT EXISTS (SELECT 1 FROM [dbo].[DIM_Time] WHERE [TimeKey] = @v_TimeKey)
        BEGIN
            INSERT INTO [dbo].[DIM_Time] (
                [TimeKey], [FullDate], [Year], [Quarter], [Month], [Week], 
                [Day], [DayOfWeek], [DayName], [IsWeekend], [WeekStartDate],
                [MonthStartDate], [QuarterStartDate], [YearStartDate], [SourceSystem]
            )
            VALUES (
                @v_TimeKey,
                @p_RankingDate,
                YEAR(@p_RankingDate),
                DATEPART(QUARTER, @p_RankingDate),
                MONTH(@p_RankingDate),
                DATEPART(WEEK, @p_RankingDate),
                DAY(@p_RankingDate),
                DATEPART(WEEKDAY, @p_RankingDate),
                FORMAT(@p_RankingDate, 'dddd'),
                CASE WHEN DATEPART(WEEKDAY, @p_RankingDate) IN (1, 7) THEN 'Y' ELSE 'N' END,
                DATEFROMPARTS(YEAR(@p_RankingDate), 1, 1),
                DATEFROMPARTS(YEAR(@p_RankingDate), MONTH(@p_RankingDate), 1),
                DATEFROMPARTS(YEAR(@p_RankingDate), (DATEPART(QUARTER, @p_RankingDate) - 1) * 3 + 1, 1),
                DATEFROMPARTS(YEAR(@p_RankingDate), 1, 1),
                'SportRadar'
            );
        END
        
        -- Step 3: Get default ranking series
        SELECT TOP 1 @v_RankingSeriesKey = [RankingSeriesKey]
        FROM [dbo].[DIM_RankingSeries]
        WHERE [IsActiveFlag] = 'Y'
        ORDER BY [EffectiveDate] DESC;
        
        IF @v_RankingSeriesKey IS NULL
        BEGIN
            INSERT INTO [dbo].[DIM_RankingSeries] (
                [SeriesSID], [SeriesName], [SeriesType], [SourceSystem], [IsActiveFlag], [EffectiveDate]
            )
            VALUES ('SR_DEFAULT', 'Default Rankings Series', 'Current', 'SportRadar', 'Y', CAST(GETUTCDATE() AS DATE));
            
            SET @v_RankingSeriesKey = SCOPE_IDENTITY();
        END
        
        -- Step 4: Insert rankings from staging
        INSERT INTO [dbo].[FACT_Rankings] (
            [CompetitorKey], [RankingSeriesKey], [TimeKey], [CategoryKey],
            [Rank], [Points], [CompetitionsPlayed], [RankMovement],
            [IsCurrentFlag], [SourceSystem], [ExtractedAt], [LoadedAt], [ETLBatchID]
        )
        SELECT
            CONVERT(BIGINT, HASHBYTES('MD5', sr.[CompetitorSID]), 2),
            @v_RankingSeriesKey,
            @v_TimeKey,
            dc.[CategoryKey],
            sr.[Rank],
            sr.[Points],
            sr.[CompetitionsPlayed],
            sr.[Movement],
            'Y',
            sr.[SourceSystem],
            sr.[ExtractedAt],
            GETUTCDATE(),
            @p_BatchID
        FROM [dbo].[STG_Rankings_Raw] sr
        INNER JOIN [dbo].[DIM_Category] dc ON sr.[CategorySID] = dc.[CategorySID]
        WHERE sr.[IsProcessedFlag] = 'N'
          AND CAST(sr.[LoadedAt] AS DATE) = @p_RankingDate;
        
        SET @v_RowsInserted = @@ROWCOUNT;
        
        -- Step 5: Mark staging records as processed
        UPDATE [dbo].[STG_Rankings_Raw]
        SET [IsProcessedFlag] = 'Y'
        WHERE [IsProcessedFlag] = 'N'
          AND CAST([LoadedAt] AS DATE) = @p_RankingDate;
        
        PRINT '[✅] SP_Load_Rankings_From_Staging completed. Rows inserted: ' + CAST(@v_RowsInserted AS VARCHAR(20));
        
    END TRY
    BEGIN CATCH
        PRINT '[❌] Error in SP_Load_Rankings_From_Staging: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END
GO

-- ============================================================================
-- SECTION 7: FINAL VERIFICATION & INDEX SUMMARY
-- ============================================================================

PRINT '========== VERIFICATION & SUMMARY ==========='
GO

-- Show all tables created
SELECT
    TABLE_NAME,
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = t.TABLE_NAME) AS ColumnCount
FROM INFORMATION_SCHEMA.TABLES t
WHERE TABLE_SCHEMA = 'dbo'
  AND (TABLE_NAME LIKE 'DIM_%' OR TABLE_NAME LIKE 'FACT_%' OR TABLE_NAME LIKE 'STG_%' OR TABLE_NAME LIKE 'BRIDGE_%')
ORDER BY TABLE_NAME;

PRINT ''
PRINT '========== ✅ STAR SCHEMA CREATION COMPLETE =========='
PRINT ''
PRINT 'Tables created:'
PRINT '  • DIM_Time'
PRINT '  • DIM_Category'
PRINT '  • DIM_Country'
PRINT '  • DIM_Venue'
PRINT '  • DIM_RankingSeries'
PRINT '  • DIM_Competitor (SCD Type 2)'
PRINT '  • DIM_Competition (SCD Type 2)'
PRINT '  • FACT_Rankings (Core Fact Table)'
PRINT '  • BRIDGE_Competitor_Competition'
PRINT '  • STG_Rankings_Raw'
PRINT '  • STG_Competitor_Changes'
PRINT ''
PRINT 'Views created:'
PRINT '  • VW_CurrentRankings'
PRINT '  • VW_Competitor_Ranking_History'
PRINT '  • VW_Data_Quality_Checks'
PRINT '  • VW_Category_Performance'
PRINT ''
PRINT 'Stored Procedures:'
PRINT '  • SP_Load_Rankings_From_Staging'
PRINT ''
PRINT 'Next Steps:'
PRINT '  1. Populate DIM_Time with historical and future dates'
PRINT '  2. Seed DIM_Category, DIM_Country from source data'
PRINT '  3. Create DIM_Competitor and DIM_Competition records'
PRINT '  4. Run ETL load using SP_Load_Rankings_From_Staging'
PRINT '  5. Execute VW_Data_Quality_Checks for validation'
GO

