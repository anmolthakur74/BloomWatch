"""
nasa_data_service.py
NASA-only data access layer for BloomWatch

Features:
- MODIS ORNL Subset API (NDVI time series)
- NASA GIBS (NDVI visualization thumbnails)
- Dynamic dataset/band handling for long-term compatibility
- Environment variable configuration for easy updates
"""

import os
import requests
import pandas as pd
from datetime import datetime, date
from typing import Optional

# ----------------------------------------------------------------------
# Configuration via environment variables (with defaults)
# ----------------------------------------------------------------------
MODIS_BASE_URL = os.getenv("MODIS_BASE_URL", "https://modis.ornl.gov/rst/api/v1")
MODIS_DATASET = os.getenv("MODIS_DATASET", "MOD13C1")
MODIS_BAND = os.getenv("MODIS_BAND", "NDVI")
GIBS_WMS = os.getenv("GIBS_WMS", "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi")


class NASAMODISService:
    """
    Service wrapper for NASA MODIS NDVI data
    """

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "BloomWatch/2.0 (NASA MODIS Client)"
        }
        self.api_url = f"{MODIS_BASE_URL}/{MODIS_DATASET}/point"

    # ------------------------------------------------------------------
    # NDVI TIME SERIES
    # ------------------------------------------------------------------
    def get_historical_ndvi_data(
        self,
        latitude: float,
        longitude: float,
        roi_size_degrees: float,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        band: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch NDVI time-series from NASA ORNL MODIS Subset API
        Returns DataFrame with columns: Date, NDVI
        """

        band = band or MODIS_BAND
        start_date = start_date or "2000-01-01"
        end_date = end_date or date.today().strftime("%Y-%m-%d")

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "startDate": start_date,
            "endDate": end_date,
            "band": band
        }

        try:
            response = requests.get(
                self.api_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"NASA MODIS request failed: {e}")

        data = payload.get("data", [])
        scale = payload.get("scale", 0.0001) or 0.0001

        rows = []
        for item in data:
            date_str = item.get("calendar_date")
            value = item.get("value")
            if date_str is None or value is None:
                continue
            try:
                ndvi = float(value) * float(scale)
                rows.append((pd.to_datetime(date_str), ndvi))
            except Exception:
                continue

        if not rows:
            return pd.DataFrame(columns=["Date", "NDVI"])

        df = pd.DataFrame(rows, columns=["Date", "NDVI"]).sort_values("Date").reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # NDVI THUMBNAIL (NASA GIBS)
    # ------------------------------------------------------------------
    def get_modis_ndvi_thumbnail(
        self,
        latitude: float,
        longitude: float,
        roi_size_degrees: float,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        width: int = 512,
        height: int = 512
    ) -> str:
        """
        Generate NASA GIBS NDVI thumbnail URL
        """

        start_date = start_date or "2000-01-01"
        end_date = end_date or date.today().strftime("%Y-%m-%d")

        half = roi_size_degrees / 2
        bbox = (
            longitude - half,
            latitude - half,
            longitude + half,
            latitude + half
        )

        # Use midpoint date for visualization
        try:
            mid_date = (
                pd.to_datetime(start_date)
                + (pd.to_datetime(end_date) - pd.to_datetime(start_date)) / 2
            ).strftime("%Y-%m-%d")
        except Exception:
            mid_date = end_date

        params = {
            "service": "WMS",
            "request": "GetMap",
            "version": "1.3.0",
            "layers": "MODIS_Terra_NDVI_8Day",
            "styles": "",
            "format": "image/png",
            "transparent": "true",
            "crs": "EPSG:4326",
            "bbox": ",".join(map(str, bbox)),
            "width": width,
            "height": height,
            "time": mid_date
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GIBS_WMS}?{query}"


# ----------------------------------------------------------------------
# Singleton instance used by FastAPI
# ----------------------------------------------------------------------
nasa_service = NASAMODISService()
