"""Local mock tests for API request construction and SportRadar API testing."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from api_requests import (
    DEFAULT_TIMEOUT_SECONDS,
    build_headers,
    build_http_error,
    build_url,
)
from tennis_etl.config import Settings
from tennis_etl.mongo_storage import MONGODB_COLLECTIONS


def validate_submit_payload(payload: dict) -> None:
    """Validate the POST body schema without external dependencies."""
    assert isinstance(payload, dict), "Payload must be a dictionary."
    assert isinstance(payload.get("name"), str), "Payload.name must be a string."
    assert payload["name"].strip(), "Payload.name must not be empty."
    assert isinstance(payload.get("status"), str), "Payload.status must be a string."
    assert payload["status"] in {
        "draft",
        "active",
        "archived",
    }, "Payload.status must be draft, active, or archived."
    assert isinstance(payload.get("metadata"), dict), "Payload.metadata must be a dict."


def validate_patch_payload(payload: dict) -> None:
    """Validate the PATCH body schema without external dependencies."""
    assert isinstance(payload, dict), "Patch payload must be a dictionary."
    assert payload, "Patch payload must contain at least one field."
    if "status" in payload:
        assert payload["status"] in {
            "draft",
            "active",
            "archived",
        }, "Patch status must be draft, active, or archived."


def validate_url(url_string: str) -> None:
    """Ensure a URL string is absolute and HTTP(S)."""
    parsed = urlparse(url_string)
    assert parsed.scheme in {"http", "https"}, "URL must be HTTP(S)."
    assert parsed.netloc, "URL hostname is required."


def test_sportradar_api(endpoint: str = "competitions.json") -> None:
    """
    Test SportRadar Tennis API and save JSON response locally.
    
    Args:
        endpoint: API endpoint to test (default: competitions.json)
    
    Returns:
        None - saves response to local JSON file
    """
    try:
        # Load configuration from environment variables
        config = Settings.from_environment()
        
        # Build API URL
        base_url = "https://api.sportradar.com/tennis"
        url = f"{base_url}/{config.access_level}/v3/{config.language_code}/{endpoint}"
        
        # Prepare headers with API key
        headers = {
            "accept": "application/json",
            "x-api-key": config.sportradar_api_key
        }
        
        print(f"📡 Testing API endpoint: {url}")
        print(f"🔑 Using access level: {config.access_level}")
        
        # Make API request
        response = requests.get(
            url, 
            headers=headers, 
            timeout=config.http_timeout_seconds
        )
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse JSON response
        data = response.json()
        
        # Create output directory if it doesn't exist
        output_dir = Path("api_responses")
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"sportradar_response_{timestamp}.json"
        
        # Save JSON response to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Success! Response saved to: {output_file}")
        print(f"📊 Response size: {len(json.dumps(data))} bytes")
        print(f"🔑 Keys in response: {list(data.keys())}")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e.response.status_code} - {e.response.reason}")
        print(f"Response: {e.response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not reach the API endpoint")
    except requests.exceptions.Timeout:
        print(f"❌ Timeout Error: Request took longer than {config.http_timeout_seconds} seconds")
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
    except json.JSONDecodeError:
        print("❌ JSON Decode Error: Response is not valid JSON")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_api_with_mongodb_storage(endpoint: str = "competitions.json") -> None:
    """
    Test SportRadar API, store response in MongoDB, and demonstrate ETL flow.
    
    Workflow: API → MongoDB → ETL Process
    
    Args:
        endpoint: API endpoint to test (default: competitions.json)
    """
    try:
        from api_requests import (
            store_api_response_to_mongodb,
            retrieve_api_response_from_mongodb,
        )
        
        # Load configuration
        config = Settings.from_environment()
        
        # Build API URL
        base_url = "https://api.sportradar.com/tennis"
        url = f"{base_url}/{config.access_level}/v3/{config.language_code}/{endpoint}"
        
        # Prepare headers with API key
        headers = {
            "accept": "application/json",
            "x-api-key": config.sportradar_api_key
        }
        
        print("\n" + "="*60)
        print("🔄 API → MongoDB → ETL Pipeline Test")
        print("="*60)
        
        print(f"\n📡 Step 1: Fetching from API endpoint: {url}")
        
        # Make API request
        response = requests.get(
            url, 
            headers=headers, 
            timeout=config.http_timeout_seconds
        )
        response.raise_for_status()
        
        # Parse JSON response
        api_data = response.json()
        print(f"✅ API Response received: {len(json.dumps(api_data))} bytes")
        print(f"   Keys: {list(api_data.keys())[:5]}...")
        
        # Determine collection type from endpoint
        if "competitions" in endpoint:
            collection_type = "competitions"
        elif "complex" in endpoint:
            collection_type = "complexes"
        elif "ranking" in endpoint:
            collection_type = "rankings"
        else:
            collection_type = "competitions"
        
        # Step 2: Store in MongoDB
        print(f"\n💾 Step 2: Storing in MongoDB (collection: {collection_type})")
        stored_data = store_api_response_to_mongodb(
            api_data,
            collection_type,
            mongo_url=config.database_url
        )
        print(f"✅ Data stored in MongoDB")
        
        # Step 3: Retrieve from MongoDB
        print(f"\n🔍 Step 3: Retrieving from MongoDB")
        retrieved_data = retrieve_api_response_from_mongodb(
            collection_type,
            mongo_url=config.database_url
        )
        
        if retrieved_data:
            print(f"✅ Successfully retrieved from MongoDB")
            print(f"   Retrieved bytes: {len(json.dumps(retrieved_data))}")
            print(f"   Data matches original: {retrieved_data == api_data}")
        else:
            print(f"⚠️  No data retrieved from MongoDB")
        
        # Step 4: Show ETL entry point
        print(f"\n🔄 Step 4: ETL Pipeline Ready")
        print(f"   MongoDB staging DB: tennis_staging")
        print(f"   Collection: {MONGODB_COLLECTIONS.get(collection_type, collection_type)}")
        print(f"   Ready for ETL transforms")
        
        print("\n" + "="*60)
        print("✅ Pipeline Test Complete!")
        print("   Run 'python -m tennis_etl.run_etl' to process ETL")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Error in API → MongoDB → ETL workflow: {e}")
        raise


if __name__ == "__main__":
    # Check if user wants to test with MongoDB storage
    if len(sys.argv) > 1 and sys.argv[1] == "--with-mongodb":
        # Run with MongoDB storage
        print("🚀 Running with MongoDB storage and ETL pipeline integration...")
        test_api_with_mongodb_storage("competitions.json")
    else:
        # Run basic API test
        print("🚀 Running basic API test...")
        test_sportradar_api("competitions.json")
        print("\n💡 Tip: Run with --with-mongodb flag to test full pipeline:")
        print("   python api_test.py --with-mongodb")
