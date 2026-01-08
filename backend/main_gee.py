from backend.gee_service import initialize_ee
initialize_ee()  # Initialize Google Earth Engine at startup

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from backend.gee_data_service import gee_service
from backend.bloom_analysis import (
    generate_user_report,
    format_user_friendly_output,
    detect_bloom_peaks,
    plot_ndvi_timeseries
)

# ==================== REQUEST MODELS ====================

class RegionRequest(BaseModel):
    latitude: float
    longitude: float
    roi_size_degrees: float = 5.0
    start_date: str = "2000-01-01"
    end_date: str

class PeaksRequest(RegionRequest):
    threshold: float = 0.2

class AnalysisRequest(RegionRequest):
    threshold: float = 0.2

# ==================== APP SETUP ====================

app = FastAPI(title="BloomWatch NDVI API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== HELPERS ====================

def get_ndvi_data(req: RegionRequest) -> pd.DataFrame:
    df = gee_service.get_historical_ndvi_data(
        latitude=req.latitude,
        longitude=req.longitude,
        roi_size_degrees=req.roi_size_degrees,
        start_date=req.start_date,
        end_date=req.end_date
    )
    if df.empty:
        raise HTTPException(404, "No NDVI data found for this region/time range")
    df['Date'] = pd.to_datetime(df['Date'])
    return df

# ==================== ROUTES ====================

@app.get("/health")
def health():
    return {"status": "ok", "engine": "GEE", "forecast": "removed (analytics only)"}

@app.post("/api/ndvi")
def ndvi(req: RegionRequest):
    df = get_ndvi_data(req)
    return {"count": len(df), "records": df.to_dict(orient="records")}

@app.post("/api/peaks")
def peaks(req: PeaksRequest):
    df = get_ndvi_data(req)
    peak_idx, props = detect_bloom_peaks(df, threshold=req.threshold)
    return {"count": len(peak_idx), "peaks": peak_idx, "heights": props.get("heights", [])}

@app.post("/api/analysis")
def analysis(req: AnalysisRequest):
    df = get_ndvi_data(req)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date', 'NDVI'])
    if df.empty:
        return {"success": False, "message": "No valid NDVI data after cleaning"}

    peak_idx, _ = detect_bloom_peaks(df, threshold=req.threshold)
    report = generate_user_report(df, peaks=peak_idx)

    response = {
        "success": True,
        "report": report,  # <-- wrap in 'report' key for frontend
        "formatted": format_user_friendly_output(report)
    }

    return response
