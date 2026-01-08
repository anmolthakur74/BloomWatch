#!/usr/bin/env python3
"""
Test script to demonstrate user-friendly analysis features
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nasa_data_service import nasa_service
from bloom_analysis import generate_user_report, format_user_friendly_output, lstm_forecast, detect_bloom_peaks
import pandas as pd
import numpy as np

def test_user_friendly_analysis():
    """Test the user-friendly analysis features"""
    print("=" * 60)
    print("TESTING USER-FRIENDLY ANALYSIS FEATURES")
    print("=" * 60)
    
    # Test different locations
    test_locations = [
        {
            "name": "California Farmland",
            "lat": 36.7783,
            "lon": -119.4179,
            "description": "Agricultural area in California"
        },
        {
            "name": "Amazon Rainforest", 
            "lat": -3.4653,
            "lon": -62.2159,
            "description": "Dense tropical forest"
        },
        {
            "name": "Sahara Desert",
            "lat": 15.0,
            "lon": 30.0,
            "description": "Arid desert region (should be land, not water)"
        },
        {
            "name": "Mumbai, India",
            "lat": 19.12,
            "lon": 72.55,
            "description": "Urban/green area near Sanjay Gandhi National Park"
        },
        {
            "name": "Atlantic Ocean",
            "lat": 30.0,
            "lon": -40.0,
            "description": "Ocean water body"
        }
    ]
    
    for location in test_locations:
        print(f"\n{'='*50}")
        print(f"LOCATION: {location['name']}")
        print(f"Coordinates: {location['lat']}, {location['lon']}")
        print(f"Description: {location['description']}")
        print(f"{'='*50}")
        
        try:
            # Get NDVI data
            df = nasa_service.get_historical_ndvi_data(
                location['lat'], 
                location['lon'], 
                2.0,  # 2 degree ROI
                "2020-01-01", 
                "2023-12-31"
            )
            
            if df.empty:
                print("No data available for this location")
                continue
            
            # Check if it's being incorrectly classified as water
            mean_ndvi = df['NDVI'].mean()
            print(f"\nMean NDVI: {mean_ndvi:.3f}")
            
            if mean_ndvi < 0.1:
                print("Classification: Water/Non-vegetated")
            elif mean_ndvi < 0.3:
                print("Classification: Sparse Vegetation/Desert")
            else:
                print("Classification: Vegetated Land")
                
            # Detect peaks
            ndvi_series = df['NDVI'].values
            peaks, _ = detect_bloom_peaks(df, threshold=0.2)
            peak_indices = peaks if isinstance(peaks, list) else peaks.tolist()
            
            # Generate forecast
            forecast_dates, forecast_values = lstm_forecast(df, future_steps=30, look_back=15)
            
            if forecast_dates is None:
                print("\nForecast: SKIPPED (very low NDVI region)")
            else:
                print(f"\nForecast: Generated {len(forecast_values)} predictions")
            
            # Generate user-friendly report
            report = generate_user_report(
                df,
                forecast_dates=forecast_dates,
                forecast_values=forecast_values,
                peaks=peak_indices
            )
            
            # Format and display
            formatted_output = format_user_friendly_output(report)
            print(formatted_output)
            
        except Exception as e:
            print(f"Error analyzing {location['name']}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*60}")
    print("USER-FRIENDLY ANALYSIS TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_user_friendly_analysis()
