-- ============================================================================
-- Tennis Rankings ETL Data Warehouse
-- SQL Server Database Setup Script for SSMS 22
-- ============================================================================
-- This script creates a complete data warehouse schema for tennis rankings data
-- with all necessary tables, relationships, and indexes.
--
-- Usage:
-- 1. Open this script in SQL Server Management Studio (SSMS)
-- 2. Update SERVER_NAME and DATABASE_NAME variables below
-- 3. Connect to your SQL Server instance
-- 4. Execute this entire script
-- ============================================================================

-- Set the target database
USE master;
GO

-- ============================================================================
-- Step 1: Create Database (if it doesn't exist)
-- ============================================================================
IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = 'TennisRankings')
BEGIN
    CREATE DATABASE [TennisRankings]
    ON PRIMARY
    (
        NAME = N'TennisRankings',
        FILENAME = N'C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\DATA\TennisRankings.mdf',
        SIZE = 100 MB,
        FILEGROWTH = 10 MB
    )
    LOG ON
    (
        NAME = N'TennisRankings_log',
        FILENAME = N'C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\DATA\TennisRankings_log.ldf',
        SIZE = 50 MB,
        FILEGROWTH = 10 MB
    );
    
    PRINT '✅ Database TennisRankings created successfully';
END
ELSE
BEGIN
    PRINT '⚠️ Database TennisRankings already exists';
END
GO

-- Switch to the new database
USE [TennisRankings];
GO

-- ============================================================================
-- Step 2: Create Core Dimension Tables
-- ============================================================================

-- Categories Table
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Categories')
BEGIN
    CREATE TABLE [dbo].[Categories]
    (
        [CategoryID] BIGINT PRIMARY KEY,
        [CategoryName] NVARCHAR(255) NOT NULL,
        [Description] NVARCHAR(MAX),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE()
    );
    
    CREATE NONCLUSTERED INDEX [IX_Categories_Name] ON [dbo].[Categories] ([CategoryName]);
    
    PRINT 'Categories table created';
END
GO

-- Competitions Table
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Competitions')
BEGIN
    CREATE TABLE [dbo].[Competitions]
    (
        [CompetitionID] BIGINT PRIMARY KEY,
        [CompetitionName] NVARCHAR(255) NOT NULL,
        [CategoryID] BIGINT NOT NULL,
        [Status] NVARCHAR(50),
        [StartDate] DATETIME2,
        [EndDate] DATETIME2,
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        CONSTRAINT [FK_Competitions_Categories] FOREIGN KEY ([CategoryID]) 
            REFERENCES [dbo].[Categories]([CategoryID])
    );
    
    CREATE NONCLUSTERED INDEX [IX_Competitions_Name] ON [dbo].[Competitions] ([CompetitionName]);
    CREATE NONCLUSTERED INDEX [IX_Competitions_CategoryID] ON [dbo].[Competitions] ([CategoryID]);
    
    PRINT 'Competitions table created';
END
GO

-- Complexes Table
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Complexes')
BEGIN
    CREATE TABLE [dbo].[Complexes]
    (
        [ComplexID] BIGINT PRIMARY KEY,
        [ComplexName] NVARCHAR(255) NOT NULL,
        [Country] NVARCHAR(100),
        [City] NVARCHAR(100),
        [Timezone] NVARCHAR(50),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE()
    );
    
    CREATE NONCLUSTERED INDEX [IX_Complexes_Name] ON [dbo].[Complexes] ([ComplexName]);
    CREATE NONCLUSTERED INDEX [IX_Complexes_City] ON [dbo].[Complexes] ([City]);
    
    PRINT 'Complexes table created';
END
GO

-- Venues Table
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Venues')
BEGIN
    CREATE TABLE [dbo].[Venues]
    (
        [VenueID] BIGINT PRIMARY KEY,
        [VenueName] NVARCHAR(255) NOT NULL,
        [ComplexID] BIGINT NOT NULL,
        [Capacity] INT,
        [Surface] NVARCHAR(50),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        CONSTRAINT [FK_Venues_Complexes] FOREIGN KEY ([ComplexID]) 
            REFERENCES [dbo].[Complexes]([ComplexID])
    );
    
    CREATE NONCLUSTERED INDEX [IX_Venues_Name] ON [dbo].[Venues] ([VenueName]);
    CREATE NONCLUSTERED INDEX [IX_Venues_ComplexID] ON [dbo].[Venues] ([ComplexID]);
    
    PRINT 'Venues table created';
END
GO

-- Competitors Table
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Competitors')
BEGIN
    CREATE TABLE [dbo].[Competitors]
    (
        [CompetitorID] BIGINT PRIMARY KEY,
        [FirstName] NVARCHAR(100),
        [LastName] NVARCHAR(100),
        [FullName] NVARCHAR(255) NOT NULL,
        [Country] NVARCHAR(100),
        [Gender] NVARCHAR(10),
        [Birthdate] DATE,
        [Status] NVARCHAR(50),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE()
    );
    
    CREATE NONCLUSTERED INDEX [IX_Competitors_FullName] ON [dbo].[Competitors] ([FullName]);
    CREATE NONCLUSTERED INDEX [IX_Competitors_Country] ON [dbo].[Competitors] ([Country]);
    CREATE NONCLUSTERED INDEX [IX_Competitors_Gender] ON [dbo].[Competitors] ([Gender]);
    
    PRINT 'Competitors table created';
END
GO

-- ============================================================================
-- Step 3: Create Fact Tables
-- ============================================================================

-- Rankings Table (Fact Table)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Rankings')
BEGIN
    CREATE TABLE [dbo].[Rankings]
    (
        [RankingID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [RankingDate] DATE NOT NULL,
        [CompetitorID] BIGINT NOT NULL,
        [CategoryID] BIGINT NOT NULL,
        [Rank] INT NOT NULL,
        [Points] INT,
        [Movement] INT,
        [Competitions] INT,
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        CONSTRAINT [FK_Rankings_Competitors] FOREIGN KEY ([CompetitorID]) 
            REFERENCES [dbo].[Competitors]([CompetitorID]),
        CONSTRAINT [FK_Rankings_Categories] FOREIGN KEY ([CategoryID]) 
            REFERENCES [dbo].[Categories]([CategoryID]),
        CONSTRAINT [UQ_Rankings_Unique] UNIQUE ([RankingDate], [CompetitorID], [CategoryID])
    );
    
    CREATE NONCLUSTERED INDEX [IX_Rankings_Date] ON [dbo].[Rankings] ([RankingDate]);
    CREATE NONCLUSTERED INDEX [IX_Rankings_CompetitorID] ON [dbo].[Rankings] ([CompetitorID]);
    CREATE NONCLUSTERED INDEX [IX_Rankings_CategoryID] ON [dbo].[Rankings] ([CategoryID]);
    CREATE NONCLUSTERED INDEX [IX_Rankings_Rank] ON [dbo].[Rankings] ([Rank]);
    
    PRINT 'Rankings table created';
END
GO

-- ============================================================================
-- Step 4: Create Staging Tables (for ETL processing)
-- ============================================================================

-- Staging table for raw API competitions data
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Staging_Competitions')
BEGIN
    CREATE TABLE [dbo].[Staging_Competitions]
    (
        [StagingID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [RawData] NVARCHAR(MAX) NOT NULL,
        [SourceID] NVARCHAR(100),
        [ProcessedFlag] BIT DEFAULT 0,
        [ErrorMessage] NVARCHAR(MAX),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [ProcessedAt] DATETIME2
    );
    
    CREATE NONCLUSTERED INDEX [IX_Staging_Competitions_Processed] 
        ON [dbo].[Staging_Competitions] ([ProcessedFlag]);
    
    PRINT 'Staging_Competitions table created';
END
GO

-- Staging table for raw API complexes data
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Staging_Complexes')
BEGIN
    CREATE TABLE [dbo].[Staging_Complexes]
    (
        [StagingID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [RawData] NVARCHAR(MAX) NOT NULL,
        [SourceID] NVARCHAR(100),
        [ProcessedFlag] BIT DEFAULT 0,
        [ErrorMessage] NVARCHAR(MAX),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [ProcessedAt] DATETIME2
    );
    
    CREATE NONCLUSTERED INDEX [IX_Staging_Complexes_Processed] 
        ON [dbo].[Staging_Complexes] ([ProcessedFlag]);
    
    PRINT 'Staging_Complexes table created';
END
GO

-- Staging table for raw API rankings data
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Staging_Rankings')
BEGIN
    CREATE TABLE [dbo].[Staging_Rankings]
    (
        [StagingID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [RawData] NVARCHAR(MAX) NOT NULL,
        [SourceID] NVARCHAR(100),
        [ProcessedFlag] BIT DEFAULT 0,
        [ErrorMessage] NVARCHAR(MAX),
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE(),
        [ProcessedAt] DATETIME2
    );
    
    CREATE NONCLUSTERED INDEX [IX_Staging_Rankings_Processed] 
        ON [dbo].[Staging_Rankings] ([ProcessedFlag]);
    
    PRINT 'Staging_Rankings table created';
END
GO

-- ============================================================================
-- Step 5: Create Audit/Tracking Tables
-- ============================================================================

-- ETL Pipeline Execution Log
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'ETL_ExecutionLog')
BEGIN
    CREATE TABLE [dbo].[ETL_ExecutionLog]
    (
        [ExecutionID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [StartTime] DATETIME2 NOT NULL,
        [EndTime] DATETIME2,
        [Status] NVARCHAR(50) NOT NULL, -- 'Running', 'Completed', 'Failed'
        [TotalRecordsProcessed] INT DEFAULT 0,
        [ErrorCount] INT DEFAULT 0,
        [ErrorDetails] NVARCHAR(MAX),
        [Duration_Seconds] INT,
        [CreatedAt] DATETIME2 DEFAULT GETUTCDATE()
    );
    
    CREATE NONCLUSTERED INDEX [IX_ETL_ExecutionLog_Status] 
        ON [dbo].[ETL_ExecutionLog] ([Status]);
    CREATE NONCLUSTERED INDEX [IX_ETL_ExecutionLog_Date] 
        ON [dbo].[ETL_ExecutionLog] ([StartTime]);
    
    PRINT 'ETL_ExecutionLog table created';
END
GO

-- ============================================================================
-- Step 6: Create Stored Procedures for Data Loading
-- ============================================================================

-- Procedure to insert/update categories
IF EXISTS (SELECT 1 FROM sys.procedures WHERE name = 'sp_Upsert_Category')
    DROP PROCEDURE [dbo].[sp_Upsert_Category];
GO

CREATE PROCEDURE [dbo].[sp_Upsert_Category]
    @CategoryID BIGINT,
    @CategoryName NVARCHAR(255),
    @Description NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS (SELECT 1 FROM [dbo].[Categories] WHERE [CategoryID] = @CategoryID)
    BEGIN
        UPDATE [dbo].[Categories]
        SET 
            [CategoryName] = @CategoryName,
            [Description] = @Description,
            [UpdatedAt] = GETUTCDATE()
        WHERE [CategoryID] = @CategoryID;
    END
    ELSE
    BEGIN
        INSERT INTO [dbo].[Categories] ([CategoryID], [CategoryName], [Description])
        VALUES (@CategoryID, @CategoryName, @Description);
    END
END;
GO

-- Procedure to insert/update rankings
IF EXISTS (SELECT 1 FROM sys.procedures WHERE name = 'sp_Upsert_Ranking')
    DROP PROCEDURE [dbo].[sp_Upsert_Ranking];
GO

CREATE PROCEDURE [dbo].[sp_Upsert_Ranking]
    @RankingDate DATE,
    @CompetitorID BIGINT,
    @CategoryID BIGINT,
    @Rank INT,
    @Points INT = NULL,
    @Movement INT = NULL,
    @Competitions INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS (SELECT 1 FROM [dbo].[Rankings] 
               WHERE [RankingDate] = @RankingDate 
               AND [CompetitorID] = @CompetitorID 
               AND [CategoryID] = @CategoryID)
    BEGIN
        UPDATE [dbo].[Rankings]
        SET 
            [Rank] = @Rank,
            [Points] = @Points,
            [Movement] = @Movement,
            [Competitions] = @Competitions,
            [UpdatedAt] = GETUTCDATE()
        WHERE [RankingDate] = @RankingDate 
          AND [CompetitorID] = @CompetitorID 
          AND [CategoryID] = @CategoryID;
    END
    ELSE
    BEGIN
        INSERT INTO [dbo].[Rankings] 
            ([RankingDate], [CompetitorID], [CategoryID], [Rank], [Points], [Movement], [Competitions])
        VALUES (@RankingDate, @CompetitorID, @CategoryID, @Rank, @Points, @Movement, @Competitions);
    END
END;
GO

-- ============================================================================
-- Step 7: Verify Database Setup
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'Database Setup Complete!';
PRINT '============================================================================';
PRINT '';
PRINT 'Tables Created:';
SELECT '   - ' + TABLE_NAME as [Table]
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;

PRINT '';
PRINT 'Summary:';
SELECT 
    'Total Tables' as [Metric],
    COUNT(*) as [Count]
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE';

PRINT '';
PRINT 'Next Steps:';
PRINT '   1. Verify all tables are created in Object Explorer';
PRINT '   2. Update your .env file with SQL Server connection string';
PRINT '   3. Run Python ETL pipeline: python -m tennis_etl.run_etl';
PRINT '';
PRINT 'Connection String Template:';
PRINT '   mssql+pyodbc://user:password@server/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server';
PRINT '';
GO
