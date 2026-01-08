"""
Google Earth Engine (GEE) service functions
"""

import ee
import os
import pandas as pd
from datetime import datetime, timedelta

def initialize_ee():
    """
    Initialize the Google Earth Engine API using project-based auth.
    """
    project_id = os.environ.get("GEE_PROJECT_ID")

    if not project_id:
        raise RuntimeError(
            "GEE_PROJECT_ID not set. Run:\n"
            "setx GEE_PROJECT_ID \"your-project-id\""
        )

    service_account = os.environ.get("GEE_SERVICE_ACCOUNT")
    json_path = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")

    if service_account and json_path:
        # For deployment (service account)
        credentials = ee.ServiceAccountCredentials(
            service_account, key_file=json_path
        )
        ee.Initialize(credentials, project=project_id)
    else:
        # For local user authentication
        ee.Initialize(project=project_id)

    print("Earth Engine initialized with project:", project_id)

def get_historical_ndvi_data(latitude: float, longitude: float,
                             roi_size_degrees: float = 5.0,
                             start_date: str = "2000-01-01",
                             end_date: str = None) -> pd.DataFrame:
    """
    Fetch historical NDVI time series from MODIS for a given lat/lon region.
    Returns empty DataFrame if no data available.
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    # Clamp coordinates to valid ranges
    latitude = max(min(latitude, 90), -90)
    longitude = max(min(longitude, 180), -180)

    # Define ROI as square
    roi = ee.Geometry.Rectangle([
        longitude - roi_size_degrees/2,
        latitude - roi_size_degrees/2,
        longitude + roi_size_degrees/2,
        latitude + roi_size_degrees/2
    ])

    # MODIS NDVI dataset
    modis = ee.ImageCollection('MODIS/061/MOD13Q1') \
        .filterBounds(roi) \
        .filterDate(start_date, end_date) \
        .select('NDVI')

    # Map over images safely
    def reduce_image(img):
        mean_dict = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=500,
            maxPixels=1e9
        )
        ndvi_value = mean_dict.get('NDVI')
        # Only create feature if NDVI exists
        return ee.Algorithms.If(ndvi_value,
                                ee.Feature(None, {
                                    'NDVI': ndvi_value,
                                    'Date': img.date().format("YYYY-MM-dd")
                                }),
                                None)

    # Apply safe mapping
    feature_collection = modis.map(reduce_image).filter(ee.Filter.notNull(['NDVI']))

    # If empty, return empty DataFrame
    try:
        features_list = feature_collection.getInfo().get('features', [])
    except Exception:
        features_list = []

    if not features_list:
        return pd.DataFrame(columns=['Date', 'NDVI'])

    # Convert to pandas
    data = []
    for f in features_list:
        props = f['properties']
        ndvi = props.get('NDVI')
        date = props.get('Date')
        if ndvi is not None:
            data.append({'Date': pd.to_datetime(date), 'NDVI': float(ndvi)/10000.0})  # scale to 0-1

    df = pd.DataFrame(data)
    df = df.sort_values('Date').reset_index(drop=True)
    return df
