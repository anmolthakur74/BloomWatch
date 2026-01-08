from .gee_service import initialize_ee
initialize_ee()  # Initialize Google Earth Engine at startup

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from scipy.signal import find_peaks

from .gee_data_service import gee_service
from .bloom_analysis import lstm_forecast, generate_user_report, format_user_friendly_output

# -------------------- Request Models --------------------

class RegionRequest(BaseModel):
    latitude: float
    longitude: float
    roi_size_degrees: float = 5.0
    start_date: str = "2000-01-01"
    end_date: str
    data_source: str = "gee"


class PeaksRequest(RegionRequest):
    threshold: float = 0.2


class ForecastRequest(RegionRequest):
    future_steps: int = 60
    look_back: int = 30


class AnalysisRequest(RegionRequest):
    threshold: float = 0.2
    future_steps: int = 60
    look_back: int = 30

# -------------------- App Setup --------------------

app = FastAPI(title="BloomWatch NDVI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Helpers --------------------

def get_ndvi_data(req: RegionRequest) -> pd.DataFrame:
    return gee_service.get_historical_ndvi_data(
        latitude=req.latitude,
        longitude=req.longitude,
        roi_size_degrees=req.roi_size_degrees,
        start_date=req.start_date,
        end_date=req.end_date
    )

# -------------------- Routes --------------------

@app.get("/health")
def health():
    return {"status": "ok", "data_sources": ["gee"]}


@app.post("/api/ndvi")
def ndvi(req: RegionRequest):
    try:
        df = get_ndvi_data(req)
        return {
            "records": df.to_dict(orient="records"),
            "count": len(df),
            "data_source": req.data_source,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/peaks")
def peaks(req: PeaksRequest):
    try:
        df = get_ndvi_data(req)
        if df.empty:
            return {"peaks": [], "count": 0}

        peak_idx, _ = find_peaks(df["NDVI"].values, height=req.threshold)
        return {"peaks": peak_idx.tolist(), "count": len(peak_idx)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/forecast")
def forecast(req: ForecastRequest):
    try:
        df = get_ndvi_data(req)
        dates, values = lstm_forecast(df, future_steps=req.future_steps, look_back=req.look_back)

        if dates is None:
            return {"skipped": True, "reason": "Water-dominant region"}

        return {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "values": [float(v) for v in values],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/analysis")
def analysis(req: AnalysisRequest):
    try:
        df = get_ndvi_data(req)
        peak_idx, _ = find_peaks(df["NDVI"].values, height=req.threshold)

        forecast_dates, forecast_values = lstm_forecast(df, future_steps=req.future_steps, look_back=req.look_back)

        report = generate_user_report(df, forecast_dates, forecast_values, peak_idx.tolist())

        return {
            "report": report,
            "formatted": format_user_friendly_output(report),
            "success": True,
        }
    except Exception as e:
        raise HTTPException(500, str(e))
