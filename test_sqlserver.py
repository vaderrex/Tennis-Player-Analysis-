"""SQL Server connection test and validation script."""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
LOGGER = logging.getLogger(__name__)


def test_sqlserver_connection() -> None:
    """Test SQL Server connection and database setup."""
    
    print("="*70)
    print("🔍 SQL Server Database Connection Test")
    print("="*70)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("\n❌ DATABASE_URL not set in .env file")
        print("\n💡 Add one of these to your .env file:")
        print("\n   Windows Authentication (Recommended):")
        print("   DATABASE_URL=mssql+pyodbc://@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server")
        print("\n   SQL Server Authentication:")
        print("   DATABASE_URL=mssql+pyodbc://sa:password@localhost/TennisRankings?driver=ODBC+Driver+17+for+SQL+Server")
        return
    
    print(f"\n📍 Connection URL: {database_url}")
    
    # Test 1: Check if pyodbc is installed
    print("\n" + "-"*70)
    print("Test 1: Check pyodbc Installation")
    print("-"*70)
    
    try:
        import pyodbc
        print(f"✅ pyodbc installed (version {pyodbc.__version__})")
    except ImportError:
        print("❌ pyodbc not installed")
        print("\n💡 Install with: pip install pyodbc")
        return
    
    # Test 2: Check available ODBC drivers
    print("\n" + "-"*70)
    print("Test 2: Available ODBC Drivers")
    print("-"*70)
    
    try:
        drivers = pyodbc.drivers()
        sql_drivers = [d for d in drivers if "SQL" in d]
        
        if sql_drivers:
            print(f"✅ Found {len(sql_drivers)} SQL Server ODBC driver(s):")
            for driver in sql_drivers:
                print(f"   - {driver}")
        else:
            print("❌ No SQL Server ODBC drivers found")
            print("\n💡 Download and install:")
            print("   https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
            return
    except Exception as e:
        print(f"❌ Error checking drivers: {e}")
        return
    
    # Test 3: Test connection
    print("\n" + "-"*70)
    print("Test 3: SQL Server Connection")
    print("-"*70)
    
    try:
        from sqlalchemy import create_engine, inspect, text
        
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT @@VERSION"))
            version = result.scalar()
            print(f"✅ Connected to SQL Server")
            print(f"   Version: {version[:80]}...")
            
    except ImportError:
        print("❌ SQLAlchemy not installed")
        print("\n💡 Install with: pip install SQLAlchemy")
        return
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Verify SQL Server is running")
        print("   2. Check connection string format")
        print("   3. Verify TennisRankings database exists")
        print("   4. Check ODBC driver version")
        return
    
    # Test 4: Check database and tables
    print("\n" + "-"*70)
    print("Test 4: Database Tables")
    print("-"*70)
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "Categories", "Competitions", "Complexes", "Venues", 
            "Competitors", "Rankings", "Staging_Competitions",
            "Staging_Complexes", "Staging_Rankings", "ETL_ExecutionLog"
        ]
        
        if tables:
            print(f"✅ Found {len(tables)} table(s):")
            for table in sorted(tables):
                status = "✅" if table in expected_tables else "⚠️"
                print(f"   {status} {table}")
        else:
            print("❌ No tables found in TennisRankings database")
            print("\n💡 Run the setup script:")
            print("   Open SQL_SERVER_SETUP.md for instructions")
            return
        
        # Check expected tables
        missing = set(expected_tables) - set(tables)
        if missing:
            print(f"\n⚠️  Missing tables: {', '.join(missing)}")
            print("   Re-run the database creation script in SSMS")
        else:
            print(f"\n✅ All {len(expected_tables)} expected tables found!")
            
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return
    
    # Test 5: Check table row counts
    print("\n" + "-"*70)
    print("Test 5: Table Data Summary")
    print("-"*70)
    
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT 
                    'Categories' as [Table], COUNT(*) as [Rows]
                FROM [Categories]
                UNION ALL
                SELECT 'Competitions', COUNT(*) FROM [Competitions]
                UNION ALL
                SELECT 'Complexes', COUNT(*) FROM [Complexes]
                UNION ALL
                SELECT 'Venues', COUNT(*) FROM [Venues]
                UNION ALL
                SELECT 'Competitors', COUNT(*) FROM [Competitors]
                UNION ALL
                SELECT 'Rankings', COUNT(*) FROM [Rankings]
                UNION ALL
                SELECT 'Staging_Competitions', COUNT(*) FROM [Staging_Competitions]
                UNION ALL
                SELECT 'Staging_Complexes', COUNT(*) FROM [Staging_Complexes]
                UNION ALL
                SELECT 'Staging_Rankings', COUNT(*) FROM [Staging_Rankings]
                ORDER BY [Table]
            """)
            
            results = connection.execute(query).fetchall()
            
            total_rows = 0
            for table_name, row_count in results:
                status = "✅" if row_count > 0 else "⚠️"
                print(f"   {status} {table_name}: {row_count:,} rows")
                total_rows += row_count
            
            print(f"\n   📊 Total rows: {total_rows:,}")
            
            if total_rows == 0:
                print("\n   ℹ️  No data yet. Run ETL pipeline to populate:")
                print("      python api_test.py --with-mongodb")
                print("      python -m tennis_etl.run_etl")
                
    except Exception as e:
        print(f"⚠️  Error checking row counts: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("✅ SQL Server Connection Test Complete!")
    print("="*70)
    
    print("\n💡 Next Steps:")
    print("   1. If all tests passed, database is ready for ETL")
    print("   2. Run API test: python api_test.py --with-mongodb")
    print("   3. Run ETL pipeline: python -m tennis_etl.run_etl")
    print("   4. Query data in SSMS or with Python")
    
    print("\n🔗 Useful commands:")
    print("   - Test connection: python test_sqlserver.py")
    print("   - Query rankings: python -c \"from tennis_etl.database import *; ...\"")
    print("   - View logs: SELECT * FROM [dbo].[ETL_ExecutionLog]")
    
    print("\n" + "="*70 + "\n")
    
    engine.dispose()


if __name__ == "__main__":
    test_sqlserver_connection()
