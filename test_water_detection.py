#!/usr/bin/env python3
"""
Test water detection functionality for Atlantic Ocean and other water bodies
"""

from nasa_data_service import nasa_service
import pandas as pd

def test_water_detection():
    """Test water detection for various locations"""
    
    # Test locations with expected classifications
    locations = [
        (0, -30, "Atlantic Ocean (Equator)", "WATER"),
        (0, -60, "Atlantic Ocean (Mid)", "WATER"),
        (40, -70, "North Atlantic", "WATER"),
        (37.7749, -122.4194, "San Francisco (Land)", "LAND"),
        (40.7128, -74.0060, "New York (Land)", "LAND"),
        (0, 0, "Gulf of Guinea (Ocean)", "WATER"),
        (15.0, 30.0, "Sahara Desert (Land)", "LAND"),
        (19.12, 72.55, "Mumbai, India (Land)", "LAND"),
        (23.4241, 12.8476, "Sahara Desert North (Land)", "LAND"),
    ]
    
    print("Water Detection Test Results")
    print("=" * 60)
    
    correct = 0
    total = 0
    
    for lat, lon, name, expected in locations:
        print(f"\nTesting: {name} ({lat}, {lon})")
        print(f"Expected: {expected}")
        
        try:
            # Get NDVI data
            df = nasa_service.get_historical_ndvi_data(
                lat, lon, 5, '2023-01-01', '2023-12-31'
            )
            
            if df.empty:
                print(f"   [FAIL] No data available")
                continue
            
            # Calculate statistics
            mean_ndvi = df['NDVI'].mean()
            min_ndvi = df['NDVI'].min()
            max_ndvi = df['NDVI'].max()
            
            # Water detection logic (matching the fixed _is_water_location)
            is_water = mean_ndvi < 0.1
            water_status = "WATER" if is_water else "LAND"
            
            print(f"   NDVI Stats: Mean={mean_ndvi:.3f}, Min={min_ndvi:.3f}, Max={max_ndvi:.3f}")
            print(f"   Detected: {water_status}")
            
            # Check if classification is correct
            total += 1
            if water_status == expected:
                print(f"   [PASS] Classification correct")
                correct += 1
            else:
                print(f"   [FAIL] Expected {expected}, got {water_status}")
            
            # Test LSTM forecast behavior
            if is_water:
                print(f"   LSTM Forecast: Should be SKIPPED (water region)")
            else:
                print(f"   LSTM Forecast: Should proceed (land region)")
                
        except Exception as e:
            print(f"   [ERROR] {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"Test Summary: {correct}/{total} correct classifications ({100*correct/total:.1f}%)")
    print("=" * 60)

def test_lstm_water_guard():
    """Test the LSTM water guard functionality"""
    print("\n" + "="*60)
    print("LSTM Water Guard Test")
    print("=" * 60)
    
    # Test water region
    print("\nTest 1: Atlantic Ocean (should skip forecast)")
    print("-" * 40)
    try:
        from bloom_analysis import lstm_forecast
        df_water = nasa_service.get_historical_ndvi_data(0, -30, 5, '2023-01-01', '2023-12-31')
        print(f"Mean NDVI: {df_water['NDVI'].mean():.3f}")
        
        dates, values = lstm_forecast(df_water, future_steps=30, look_back=30)
        
        if dates is None or values is None:
            print("[PASS] LSTM correctly skipped forecasting for water region")
        else:
            print("[FAIL] LSTM should have skipped water region")
            
    except Exception as e:
        print(f"[ERROR] Error testing water region: {e}")
        import traceback
        traceback.print_exc()
    
    # Test land region
    print("\nTest 2: San Francisco (should proceed with forecast)")
    print("-" * 40)
    try:
        df_land = nasa_service.get_historical_ndvi_data(37.7749, -122.4194, 5, '2023-01-01', '2023-12-31')
        print(f"Mean NDVI: {df_land['NDVI'].mean():.3f}")
        
        dates, values = lstm_forecast(df_land, future_steps=30, look_back=30)
        
        if dates is not None and values is not None:
            print(f"[PASS] LSTM generated forecast for land region ({len(values)} predictions)")
        else:
            print("[FAIL] LSTM should have generated forecast for land region")
            
    except Exception as e:
        print(f"[ERROR] Error testing land region: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Sahara Desert (land but sparse vegetation)
    print("\nTest 3: Sahara Desert at (15, 30) - should be LAND, not water")
    print("-" * 40)
    try:
        df_sahara = nasa_service.get_historical_ndvi_data(15.0, 30.0, 5, '2023-01-01', '2023-12-31')
        mean_ndvi = df_sahara['NDVI'].mean()
        print(f"Mean NDVI: {mean_ndvi:.3f}")
        
        if mean_ndvi >= 0.1:
            print("[PASS] Correctly identified as LAND (sparse vegetation/desert)")
        else:
            print("[FAIL] Incorrectly classified as water")
        
        dates, values = lstm_forecast(df_sahara, future_steps=30, look_back=30)
        
        if dates is not None and values is not None:
            print(f"[PASS] LSTM generated forecast for desert region ({len(values)} predictions)")
        else:
            print("[INFO] LSTM skipped forecast (NDVI may still be too low)")
            
    except Exception as e:
        print(f"[ERROR] Error testing Sahara: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Mumbai (land with vegetation)
    print("\nTest 4: Mumbai, India at (19.12, 72.55) - should be LAND")
    print("-" * 40)
    try:
        df_mumbai = nasa_service.get_historical_ndvi_data(19.12, 72.55, 5, '2023-01-01', '2023-12-31')
        mean_ndvi = df_mumbai['NDVI'].mean()
        print(f"Mean NDVI: {mean_ndvi:.3f}")
        
        if mean_ndvi >= 0.1:
            print("[PASS] Correctly identified as LAND")
        else:
            print("[FAIL] Incorrectly classified as water")
        
        dates, values = lstm_forecast(df_mumbai, future_steps=30, look_back=30)
        
        if dates is not None and values is not None:
            print(f"[PASS] LSTM generated forecast for Mumbai region ({len(values)} predictions)")
        else:
            print("[INFO] LSTM skipped forecast")
            
    except Exception as e:
        print(f"[ERROR] Error testing Mumbai: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_water_detection()
    test_lstm_water_guard()