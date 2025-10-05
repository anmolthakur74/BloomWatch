"""
FastAPI backend for BloomWatch using NASA data services instead of Google Earth Engine.
This provides a more reliable alternative to GEE with NASA MODIS and GIBS data.
"""

from typing import Optional, List, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import requests
import os
import sys

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nasa_data_service import nasa_service
from bloom_analysis import detect_bloom_peaks, lstm_forecast, generate_user_report, format_user_friendly_output


class RegionRequest(BaseModel):
    latitude: float = Field(..., description="Latitude center of ROI")
    longitude: float = Field(..., description="Longitude center of ROI")
    roi_size_degrees: float = Field(5.0, description="ROI size in degrees (square)")
    start_date: str = Field("2000-01-01", description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    data_source: str = Field("nasa", description="Data source: 'nasa'")


class PeaksRequest(RegionRequest):
    threshold: float = Field(0.2, description="NDVI threshold for bloom detection")


class ForecastRequest(RegionRequest):
    future_steps: int = Field(60, description="Days to forecast ahead")
    look_back: int = Field(30, description="LSTM look-back window")


class AnalysisRequest(RegionRequest):
    threshold: float = Field(0.2, description="NDVI threshold for bloom detection")
    future_steps: int = Field(60, description="Days to forecast ahead")
    look_back: int = Field(30, description="LSTM look-back window")


app = FastAPI(title="BloomWatch NASA API", version="2.0.0")

# CORS so the React frontend can call the API locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_ndvi_data(req: RegionRequest) -> pd.DataFrame:
    """Get NDVI data using NASA services only."""
    return nasa_service.get_historical_ndvi_data(
        req.latitude,
        req.longitude,
        req.roi_size_degrees,
        req.start_date,
        req.end_date
    )


@app.get("/health")
def health():
    return {"status": "ok", "data_sources": ["nasa"]}


@app.post("/api/ndvi")
def get_ndvi(req: RegionRequest):
    """Get NDVI time series data"""
    try:
        df = get_ndvi_data(req)
        return {
            "records": df.to_dict(orient="records"),
            "data_source": req.data_source,
            "count": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/peaks")
def get_peaks(req: PeaksRequest):
    """Detect bloom peaks in NDVI data"""
    try:
        df = get_ndvi_data(req)
        if df.empty:
            return {"peaks": [], "count": 0, "data_source": req.data_source}
        
        ndvi_series = df['NDVI'].values
        peak_idx, _ = find_peaks(ndvi_series, height=req.threshold)
        peaks_list = [int(p) for p in peak_idx]
        
        return {
            "peaks": peaks_list,
            "count": len(peaks_list),
            "data_source": req.data_source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/forecast")
def forecast(req: ForecastRequest):
    """Generate LSTM forecast for NDVI data"""
    try:
        df = get_ndvi_data(req)
        if df.empty:
            return {"skipped": True, "reason": "No NDVI data available"}
        
        dates, values = lstm_forecast(df, future_steps=req.future_steps, look_back=req.look_back)
        if dates is None or values is None:
            return {"skipped": True, "reason": "avg NDVI < 0.1 indicates water"}
        
        # Ensure dates serialized as ISO strings
        dates_str = [pd.to_datetime(d).strftime('%Y-%m-%d') for d in dates]
        return {
            "skipped": False,
            "dates": dates_str,
            "values": [float(v) for v in values],
            "data_source": req.data_source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ndvi-thumb")
def ndvi_thumb(req: RegionRequest):
    """Get NDVI thumbnail URL"""
    try:
        thumb_url = nasa_service.get_modis_ndvi_thumbnail(
            req.latitude,
            req.longitude,
            req.roi_size_degrees,
            req.start_date,
            req.end_date
        )
        return {"url": thumb_url, "data_source": req.data_source}
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analysis")
def get_analysis(req: AnalysisRequest):
    """Get comprehensive user-friendly analysis with interpretations and recommendations"""
    try:
        df = get_ndvi_data(req)
        if df.empty:
            return {
                "error": "No NDVI data available",
                "data_source": req.data_source
            }
        
        # Detect peaks
        ndvi_series = df['NDVI'].values
        peak_idx, _ = find_peaks(ndvi_series, height=req.threshold)
        peaks_list = [int(p) for p in peak_idx]
        
        # Generate forecast
        forecast_dates, forecast_values = lstm_forecast(df, future_steps=req.future_steps, look_back=req.look_back)
        
        # Generate comprehensive report
        report = generate_user_report(
            df, 
            forecast_dates=forecast_dates, 
            forecast_values=forecast_values, 
            peaks=peaks_list
        )
        
        # Format for user-friendly output
        formatted_output = format_user_friendly_output(report)
        
        return {
            "report": report,
            "formatted_output": formatted_output,
            "data_source": req.data_source,
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-sources")
def get_data_sources():
    """Get available data sources (NASA only)."""
    return {
        "sources": [
            {
                "id": "nasa",
                "name": "NASA MODIS/GIBS",
                "description": "NASA MODIS data via GIBS and CMR APIs",
                "reliable": True,
                "authentication_required": False
            }
        ]
    }


def _fetch_modis_subset_ndvi(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch reference NDVI from NASA ORNL MODIS Subset API (MOD13C1 NDVI).
    Returns a DataFrame with columns: Date (datetime64), NDVI (float).
    """
    url = (
        "https://modis.ornl.gov/rst/api/v1/MOD13C1/point"
        f"?latitude={lat}&longitude={lon}&startDate={start_date}&endDate={end_date}&band=NDVI"
    )
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": "BloomWatch/validate"})
        r.raise_for_status()
        payload = r.json()
    except requests.exceptions.RequestException as e:
        # Re-raise with clear message so caller can handle gracefully
        raise RuntimeError(f"Reference request failed: {getattr(e.response,'status_code',None)} {str(e)}")
    data = payload.get("data", [])
    scale = payload.get("scale", 0.0001) or 0.0001
    rows: List[Tuple[pd.Timestamp, float]] = []
    for item in data:
        try:
            date_str = item.get("calendar_date")
            val = item.get("value")
            if date_str is None or val is None:
                continue
            rows.append((pd.to_datetime(date_str), float(val) * float(scale)))
        except Exception:
            continue
    if not rows:
        return pd.DataFrame(columns=["Date", "NDVI"])
    df = pd.DataFrame(rows, columns=["Date", "NDVI"]).sort_values("Date").reset_index(drop=True)
    return df


## Validation endpoint removed per user request


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
