"""
nasa_data_service.py
NASA-only data access layer for BloomWatch

Uses:
- MODIS ORNL Subset API (NDVI time series)
- NASA GIBS (NDVI visualization thumbnails)

NO Google Earth Engine required
"""

import requests
import pandas as pd
from datetime import datetime
from typing import Optional


class NASAMODISService:
    """
    Service wrapper for NASA MODIS NDVI data
    """

    ORNL_POINT_API = "https://modis.ornl.gov/rst/api/v1/MOD13C1/point"
    GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "BloomWatch/2.0 (NASA MODIS Client)"
        }

    # ------------------------------------------------------------------
    # NDVI TIME SERIES
    # ------------------------------------------------------------------
    def get_historical_ndvi_data(
        self,
        latitude: float,
        longitude: float,
        roi_size_degrees: float,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch NDVI time-series from NASA ORNL MODIS Subset API

        Returns DataFrame:
        ┌────────────┬────────┐
        │ Date       │ NDVI   │
        └────────────┴────────┘
        """

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "startDate": start_date,
            "endDate": end_date,
            "band": "NDVI"
        }

        try:
            response = requests.get(
                self.ORNL_POINT_API,
                params=params,
                timeout=self.timeout,
                headers=self.headers
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

        df = (
            pd.DataFrame(rows, columns=["Date", "NDVI"])
            .sort_values("Date")
            .reset_index(drop=True)
        )

        return df

    # ------------------------------------------------------------------
    # NDVI THUMBNAIL (NASA GIBS)
    # ------------------------------------------------------------------
    def get_modis_ndvi_thumbnail(
        self,
        latitude: float,
        longitude: float,
        roi_size_degrees: float,
        start_date: str,
        end_date: str,
        width: int = 512,
        height: int = 512
    ) -> str:
        """
        Generate NASA GIBS NDVI thumbnail URL
        """

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

        # Construct final URL
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.GIBS_WMS}?{query}"


# ----------------------------------------------------------------------
# Singleton instance used by FastAPI
# ----------------------------------------------------------------------
nasa_service = NASAMODISService()
