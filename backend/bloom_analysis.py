"""
Analytics-focused NDVI analysis without forecasting.
Generates trends, bloom peaks, vegetation health, and recommendations
based only on available data points.
"""

import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import matplotlib
matplotlib.use("Agg")
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

# -------------------- Plotting --------------------

def plot_ndvi_timeseries(df, ndvi_column="NDVI"):
    """Scatter plot of NDVI over time (sparse points allowed)"""
    if df.empty or plt is None:
        return None
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(df['Date'], df[ndvi_column], color="blue", alpha=0.7, label="NDVI")
    if len(df) > 3:
        # Optional smoothed trend using rolling average
        df['NDVI_smooth'] = df[ndvi_column].rolling(window=3, center=True).mean()
        ax.plot(df['Date'], df['NDVI_smooth'], color="red", linewidth=2, label="Smoothed NDVI")
    ax.set_title("NDVI Time Series")
    ax.set_xlabel("Date")
    ax.set_ylabel("NDVI")
    ax.set_ylim(-0.1, 1.0)
    ax.grid(True)
    ax.legend()
    return fig

# -------------------- Bloom Peak Detection --------------------

def detect_bloom_peaks(df, ndvi_column="NDVI", threshold=0.2):
    """Detect NDVI bloom peaks above threshold"""
    if df.empty:
        return [], {}
    ndvi_series = df[ndvi_column].values
    peaks, props = find_peaks(ndvi_series, height=threshold)
    return peaks.tolist(), {k: [float(v) for v in vals] for k, vals in props.items()}

# -------------------- NDVI Analytics --------------------

def calculate_trends(df, ndvi_column="NDVI"):
    """Compute simple trend (slope) over available NDVI points"""
    if df.empty or len(df) < 2:
        return 0.0
    x = np.arange(len(df))
    y = df[ndvi_column].values
    slope = np.polyfit(x, y, 1)[0]
    return float(slope)

def interpret_ndvi_value(ndvi_value):
    if ndvi_value < -0.1: return "Water Body", "Area is water"
    elif ndvi_value < 0.1: return "Bare Soil", "Very little vegetation"
    elif ndvi_value < 0.2: return "Sparse Vegetation", "Very little plant life"
    elif ndvi_value < 0.4: return "Moderate Vegetation", "Grasslands, shrubs"
    elif ndvi_value < 0.6: return "Healthy Vegetation", "Good plant health"
    elif ndvi_value < 0.8: return "Dense Vegetation", "Very healthy plants"
    else: return "Very Dense Vegetation", "Extremely healthy vegetation"

def get_vegetation_health_status(mean_ndvi, trend):
    if mean_ndvi < 0.1: return "Non-vegetated/Bare Area", "Very low NDVI"
    elif mean_ndvi < 0.3:
        if trend > 0.01: return "Improving", "Vegetation getting healthier"
        elif trend < -0.01: return "Declining", "Vegetation declining"
        else: return "Stable", "Vegetation stable"
    elif mean_ndvi < 0.6:
        if trend > 0.01: return "Growing", "Vegetation actively growing"
        elif trend < -0.01: return "Stressed", "Vegetation under stress"
        else: return "Healthy", "Vegetation in good condition"
    else:
        if trend > 0.01: return "Thriving", "Vegetation thriving"
        elif trend < -0.01: return "Peak Declining", "Vegetation past peak"
        else: return "Peak Health", "Vegetation at peak health"

# -------------------- Recommendations --------------------

def get_seasonal_recommendations(month, ndvi_value):
    recs = []
    if month in [12,1,2]: recs.append("Winter dormancy" if ndvi_value<0.3 else "Unusual winter growth")
    elif month in [3,4,5]: recs.append("Early spring growth" if ndvi_value<0.4 else "Active spring growth")
    elif month in [6,7,8]: recs.append("Summer stress" if ndvi_value<0.5 else "Peak summer growth")
    else: recs.append("Fall dormancy" if ndvi_value<0.4 else "Extended growing season")
    return recs

def get_management_recommendations(ndvi_value, trend):
    recs = []
    if ndvi_value < 0.2: recs += ["Consider soil improvement or irrigation", "Check for pests"]
    elif ndvi_value < 0.4: recs += ["Monitor plant health", "Fertilize if needed"]
    elif ndvi_value < 0.6: recs += ["Good plant health - maintain practices"]
    else: recs += ["Excellent plant health - continue management"]
    if trend < -0.02: recs.append("URGENT: Vegetation health declining")
    elif trend > 0.02: recs.append("Positive trend - continue current management")
    return recs

# -------------------- Report Generation --------------------

def generate_user_report(df, peaks=None):
    report = {"summary": {}, "current_status": {}, "trends": {}, "recommendations": {}, "peaks": {}}
    if df.empty: return report

    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    mean_ndvi = float(df['NDVI'].mean())
    trend = calculate_trends(df)

    current_ndvi = float(df['NDVI'].iloc[-1])
    current_date = df['Date'].iloc[-1]
    current_month = current_date.month

    veg_type, veg_desc = interpret_ndvi_value(current_ndvi)
    health_status, health_desc = get_vegetation_health_status(mean_ndvi, trend)
    seasonal_recs = get_seasonal_recommendations(current_month, current_ndvi)
    management_recs = get_management_recommendations(current_ndvi, trend)

    report["summary"] = {
        "analysis_period": f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')}",
        "data_points": len(df)
    }
    report["current_status"] = {
        "vegetation_type": veg_type,
        "description": veg_desc,
        "health_status": health_status,
        "health_description": health_desc,
        "current_ndvi": round(current_ndvi,3),
        "date": current_date.strftime('%Y-%m-%d')
    }
    report["trends"] = {
        "mean_ndvi": round(mean_ndvi,3),
        "trend_value": round(trend,4),
        "trend_direction": "Improving" if trend>0.01 else "Declining" if trend<-0.01 else "Stable"
    }
    report["recommendations"] = {"seasonal": seasonal_recs, "management": management_recs}

    if peaks:
        peak_dates = [df['Date'].iloc[p].strftime('%Y-%m-%d') for p in peaks]
        peak_ndvi_values = [round(float(df['NDVI'].iloc[p]),3) for p in peaks]
        report["peaks"] = {"total_peaks": len(peaks), "peak_dates": peak_dates, "peak_ndvi_values": peak_ndvi_values}

    return report

def format_user_friendly_output(report):
    output = ["BLOOMWATCH ANALYSIS REPORT", "="*50]
    output += [f"Analysis Period: {report['summary'].get('analysis_period','')}",
               f"Data Points: {report['summary'].get('data_points',0)}"]
    output += [f"Current Vegetation: {report['current_status'].get('vegetation_type','')}",
               f"Health Status: {report['current_status'].get('health_status','')}",
               f"Current NDVI: {report['current_status'].get('current_ndvi','')}"]
    output += ["\nSeasonal Recommendations:"] + [f" - {r}" for r in report.get('recommendations',{}).get('seasonal',[])]
    output += ["Management Recommendations:"] + [f" - {r}" for r in report.get('recommendations',{}).get('management',[])]
    if report.get('peaks') and report['peaks'].get('total_peaks',0) > 0:
        output += [f"\nDetected Bloom Events ({report['peaks']['total_peaks']} peaks)"]
        for d,v in zip(report['peaks']['peak_dates'], report['peaks']['peak_ndvi_values']):
            output.append(f" - {d}: NDVI={v}")
    return "\n".join(output)

