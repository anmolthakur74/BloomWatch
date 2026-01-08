import ee
import pandas as pd
from datetime import date

class GEEService:
    """
    Google Earth Engine service for NDVI time-series.
    Uses MODIS/006/MOD13Q1 dataset (16-day NDVI, 250m resolution).
    """

    def __init__(self):
        # Dataset name in GEE
        self.modis_dataset = 'MODIS/006/MOD13Q1'

    def get_historical_ndvi_data(
        self,
        latitude: float,
        longitude: float,
        roi_size_degrees: float = 5.0,
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Fetch NDVI time-series for a given point.
        Returns a pandas DataFrame with columns: Date, NDVI
        """

        start_date = start_date or "2000-01-01"
        end_date = end_date or date.today().strftime("%Y-%m-%d")

        # Define region of interest
        point = ee.Geometry.Point([longitude, latitude])

        # Filter MODIS NDVI collection
        collection = (
            ee.ImageCollection(self.modis_dataset)
            .filterDate(start_date, end_date)
            .select('NDVI')
        )

        def sample_image(image):
            """Return a Feature with date and NDVI value at the point"""
            sample = image.sample(point, scale=250).first()
            date_str = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
            ndvi_val = ee.Number(sample.get('NDVI')) if sample else ee.Number(None)
            return ee.Feature(None, {'Date': date_str, 'NDVI': ndvi_val})

        sampled = collection.map(sample_image).filter(ee.Filter.notNull(['NDVI']))
        try:
            features = sampled.getInfo()['features']
        except ee.EEException as e:
            raise RuntimeError(f"GEE NDVI request failed: {e}")

        rows = [(f['properties']['Date'], f['properties']['NDVI'] / 10000.0) for f in features if f['properties']['NDVI'] is not None]

        if not rows:
            return pd.DataFrame(columns=['Date', 'NDVI'])

        df = pd.DataFrame(rows, columns=['Date', 'NDVI']).sort_values('Date').reset_index(drop=True)
        return df

# Singleton for FastAPI
gee_service = GEEService()
