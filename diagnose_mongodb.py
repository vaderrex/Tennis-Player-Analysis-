"""Diagnostic script to check MongoDB connection and stored data."""

from __future__ import annotations

import json
import logging
import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
LOGGER = logging.getLogger(__name__)


def diagnose_mongodb() -> None:
    """Run diagnostic checks on MongoDB connection and data."""
    
    mongo_url = os.getenv("DATABASE_URL")
    if not mongo_url:
        print("❌ DATABASE_URL not set in .env file")
        print("   Example: DATABASE_URL=mongodb://user:pass@localhost:27017/database")
        return
    
    print("="*70)
    print("🔍 MongoDB Diagnostic Report")
    print("="*70)
    
    print(f"\n📍 MongoDB URL: {mongo_url}")
    
    # Test 1: Connection
    print("\n" + "-"*70)
    print("Test 1: Connection")
    print("-"*70)
    
    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("✅ Successfully connected to MongoDB")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Is MongoDB running? (mongod process)")
        print("   2. Check connection string format")
        print("   3. Verify host/port are correct")
        print("   4. Check firewall/network access")
        return
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return
    
    # Test 2: List databases
    print("\n" + "-"*70)
    print("Test 2: Available Databases")
    print("-"*70)
    
    try:
        databases = client.list_database_names()
        if databases:
            print(f"✅ Found {len(databases)} database(s):")
            for db_name in databases:
                print(f"   - {db_name}")
        else:
            print("⚠️  No databases found")
    except Exception as e:
        print(f"❌ Error listing databases: {e}")
    
    # Test 3: Check tennis_staging database
    print("\n" + "-"*70)
    print("Test 3: Tennis Staging Database")
    print("-"*70)
    
    staging_db_name = "tennis_staging"
    try:
        db = client[staging_db_name]
        collections = db.list_collection_names()
        
        if collections:
            print(f"✅ Found {len(collections)} collection(s) in '{staging_db_name}':")
            for coll_name in collections:
                print(f"   - {coll_name}")
        else:
            print(f"⚠️  No collections in '{staging_db_name}' database")
            print("   (This is expected if no data has been stored yet)")
    except Exception as e:
        print(f"❌ Error accessing '{staging_db_name}': {e}")
    
    # Test 4: Check for data in each collection
    print("\n" + "-"*70)
    print("Test 4: Data in Collections")
    print("-"*70)
    
    expected_collections = ["raw_competitions", "raw_complexes", "raw_rankings"]
    
    for coll_name in expected_collections:
        try:
            db = client[staging_db_name]
            collection = db[coll_name]
            count = collection.count_documents({})
            
            if count > 0:
                print(f"\n✅ {coll_name}: {count} document(s)")
                
                # Show first document (sample)
                sample = collection.find_one()
                if sample:
                    # Convert ObjectId to string for display
                    sample_str = json.dumps(
                        sample,
                        indent=2,
                        default=str
                    )
                    lines = sample_str.split('\n')
                    
                    print("   Sample document (first 20 lines):")
                    for line in lines[:20]:
                        print(f"   {line}")
                    
                    if len(lines) > 20:
                        print(f"   ... ({len(lines) - 20} more lines)")
            else:
                print(f"\n⚠️  {coll_name}: 0 documents")
                print("   (Run 'python api_test.py --with-mongodb' to populate)")
                
        except Exception as e:
            print(f"\n⚠️  {coll_name}: Error checking collection - {e}")
    
    # Test 5: Check raw database (if using different URL)
    print("\n" + "-"*70)
    print("Test 5: Check Direct Database from URL")
    print("-"*70)
    
    try:
        # Extract database name from URL
        if "//" in mongo_url:
            url_parts = mongo_url.split("/")
            if len(url_parts) > 3:
                db_from_url = url_parts[3].split("?")[0]
                if db_from_url:
                    print(f"📍 Database from URL: {db_from_url}")
                    db = client[db_from_url]
                    collections = db.list_collection_names()
                    
                    if collections:
                        print(f"✅ Collections in '{db_from_url}': {collections}")
                    else:
                        print(f"⚠️  No collections in '{db_from_url}'")
    except Exception as e:
        print(f"ℹ️  Skipping direct database check: {e}")
    
    # Summary and next steps
    print("\n" + "="*70)
    print("📋 Summary & Next Steps")
    print("="*70)
    
    db = client[staging_db_name]
    collections = db.list_collection_names()
    total_docs = sum(db[c].count_documents({}) for c in collections)
    
    if total_docs > 0:
        print(f"✅ MongoDB is working! Found {total_docs} document(s)")
        print("\n   Next: Run ETL pipeline")
        print("   $ python -m tennis_etl.run_etl")
    else:
        print("❌ No data found in MongoDB")
        print("\n   Next steps:")
        print("   1. Run API test to fetch data:")
        print("      $ python api_test.py --with-mongodb")
        print("   2. Check for errors in the output")
        print("   3. Re-run this diagnostic script to verify data was stored")
    
    print("\n" + "="*70 + "\n")
    
    client.close()


if __name__ == "__main__":
    diagnose_mongodb()
