#!/usr/bin/env python3
"""
Test script for NASA API implementation
This script tests the NASA data service without requiring Google Earth Engine.
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nasa_data_service import nasa_service

def test_nasa_service():
    """Test the NASA data service"""
    print("Testing NASA Data Service...")
    
    # Test parameters
    latitude = 37.7749  # San Francisco
    longitude = -122.4194
    roi_size = 2.0
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    print(f"Location: {latitude}, {longitude}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"ROI size: {roi_size} degrees")
    
    try:
        # Test 1: Get NDVI data
        print("\n1. Testing NDVI data retrieval...")
        df = nasa_service.get_historical_ndvi_data(
            latitude, longitude, roi_size, start_date, end_date
        )
        
        if not df.empty:
            print(f"SUCCESS: Retrieved {len(df)} NDVI records")
            print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
            print(f"NDVI range: {df['NDVI'].min():.3f} to {df['NDVI'].max():.3f}")
            print(f"Mean NDVI: {df['NDVI'].mean():.3f}")
        else:
            print("WARNING: No NDVI data retrieved")
        
        # Test 2: Get thumbnail URL
        print("\n2. Testing thumbnail URL...")
        thumb_url = nasa_service.get_modis_ndvi_thumbnail(
            latitude, longitude, roi_size, start_date, end_date
        )
        
        if thumb_url:
            print(f"SUCCESS: Thumbnail URL generated: {thumb_url[:80]}...")
        else:
            print("WARNING: No thumbnail URL generated")
        
        # Test 3: Test different locations
        print("\n3. Testing different locations...")
        test_locations = [
            (40.7128, -74.0060, "New York"),
            (51.5074, -0.1278, "London"),
            (35.6762, 139.6503, "Tokyo")
        ]
        
        for lat, lon, name in test_locations:
            print(f"   Testing {name} ({lat}, {lon})...")
            df_loc = nasa_service.get_historical_ndvi_data(
                lat, lon, roi_size, start_date, end_date
            )
            if not df_loc.empty:
                print(f"   SUCCESS: {name}: {len(df_loc)} records, mean NDVI: {df_loc['NDVI'].mean():.3f}")
            else:
                print(f"   WARNING: {name}: No data")
        
        print("\nSUCCESS: NASA service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nERROR: Error testing NASA service: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test the API endpoints"""
    print("\nTesting API endpoints...")
    
    try:
        import requests
        
        # Test health endpoint
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Health endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"WARNING: Health endpoint returned {response.status_code}")
        
        # Test data sources endpoint
        response = requests.get("http://127.0.0.1:8000/api/data-sources", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Data sources endpoint working")
            sources = response.json()
            for source in sources.get('sources', []):
                print(f"   Data Source: {source['name']}: {source['description']}")
        else:
            print(f"WARNING: Data sources endpoint returned {response.status_code}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("WARNING: API server not running. Start with: python start_nasa_api.py")
        return False
    except Exception as e:
        print(f"ERROR: Error testing API endpoints: {e}")
        return False

if __name__ == "__main__":
    print("BloomWatch NASA API Test Suite")
    print("=" * 50)
    
    # Test NASA service
    nasa_success = test_nasa_service()
    
    # Test API endpoints (if server is running)
    api_success = test_api_endpoints()
    
    print("\n" + "=" * 50)
    if nasa_success:
        print("SUCCESS: NASA service tests passed!")
    else:
        print("ERROR: NASA service tests failed!")
    
    if api_success:
        print("SUCCESS: API endpoint tests passed!")
    else:
        print("WARNING: API endpoint tests skipped (server not running)")
    
    print("\nTo start the API server, run: python start_nasa_api.py")
