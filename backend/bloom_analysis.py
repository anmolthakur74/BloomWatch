"""
Utility functions for analyzing bloom events using NDVI data from Google Earth Engine
"""

import pandas as pd
import numpy as np
from scipy.signal import find_peaks

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend for headless servers
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None


# -------------------- Plotting --------------------

def plot_ndvi_timeseries(df, ndvi_column="NDVI"):
    """Plot NDVI time series"""
    if df.empty or plt is None:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df['Date'], df[ndvi_column], linestyle='-', color="blue", alpha=0.7, label="NDVI")

    if len(df) > 10:
        df['NDVI_smooth'] = df[ndvi_column].rolling(window=5, center=True).mean()
        ax.plot(df['Date'], df['NDVI_smooth'], color="red", linewidth=2, label="Smoothed NDVI")

    ax.set_title("NDVI Time Series (Scaled 0-1)")
    ax.set_xlabel("Date")
    ax.set_ylabel("NDVI")
    ax.set_ylim(-0.1, 1.0)
    ax.legend()
    ax.grid(True)
    return fig


def detect_bloom_peaks(df, ndvi_column="NDVI", threshold=0.2, show_plot=False):
    """Detect bloom peaks in NDVI data"""
    if df.empty:
        return [], {}

    ndvi_series = df[ndvi_column].values
    peaks, props = find_peaks(ndvi_series, height=threshold)

    if plt is not None and show_plot:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df['Date'], ndvi_series, color="blue", label="NDVI")
        ax.plot(df['Date'].iloc[peaks], ndvi_series[peaks], "rx", label="Bloom Peaks")
        ax.legend()
        ax.set_title("Detected Bloom Events")
        ax.set_xlabel("Date")
        ax.set_ylabel("NDVI")
        ax.set_ylim(-0.1, 1.0)
        ax.grid(True)
        plt.close(fig)  # Avoid GUI issues

    return peaks.tolist(), {k: [float(v) for v in vals] for k, vals in props.items()}


# -------------------- Forecasting --------------------

def lstm_forecast(df, future_steps=60, look_back=30, ndvi_column="NDVI", anchor_end_date: str | None = None):
    """LSTM forecasting of NDVI time series"""
    if df.empty or df[ndvi_column].mean() < 0.05:
        return None, None

    scaler = MinMaxScaler(feature_range=(0, 1))
    dataset = scaler.fit_transform(df[[ndvi_column]].values.astype(float))

    if len(dataset) <= look_back + 5:
        look_back = max(5, len(dataset) // 3)

    train_size = int(len(dataset) * 0.8)
    train, test = dataset[:train_size], dataset[train_size:]

    def create_sequences(data, look_back):
        X, y = [], []
        for i in range(len(data) - look_back):
            X.append(data[i:i + look_back, 0])
            y.append(data[i + look_back, 0])
        return np.array(X), np.array(y)

    X_train, y_train = create_sequences(train, look_back)
    X_test, y_test = create_sequences(test, look_back)

    if X_train.size == 0:
        return None, None

    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
    if X_test.size > 0:
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
    else:
        X_test, y_test = None, None

    model = Sequential()
    model.add(LSTM(32, return_sequences=True, input_shape=(look_back, 1)))
    model.add(Dropout(0.15))
    model.add(LSTM(32, return_sequences=False))
    model.add(Dropout(0.15))
    model.add(Dense(1))
    model.compile(optimizer="adam", loss="mean_squared_error")
    model.fit(X_train, y_train, epochs=8, batch_size=32, verbose=0)

    # Generate future predictions
    last_seq = dataset[-look_back:]
    future_preds = []
    current_seq = last_seq.reshape(1, look_back, 1)

    for _ in range(future_steps):
        next_pred = float(model.predict(current_seq, verbose=0)[0][0])
        future_preds.append(next_pred)
        current_seq = np.append(current_seq[:, 1:, :], [[[next_pred]]], axis=1)

    future_preds = scaler.inverse_transform(np.array(future_preds).reshape(-1, 1)).flatten()

    # Forecast dates
    if anchor_end_date:
        start_dt = pd.to_datetime(anchor_end_date) + pd.Timedelta(days=1)
    else:
        start_dt = df['Date'].iloc[-1] + pd.Timedelta(days=1)

    future_dates = pd.date_range(start=start_dt, periods=future_steps)
    return future_dates, [float(v) for v in future_preds]


# -------------------- NDVI Interpretation --------------------

def interpret_ndvi_value(ndvi_value):
    """Convert NDVI value to user-friendly interpretation"""
    if ndvi_value < -0.1:
        return "Water Body", "This area is water (ocean, lake, river)"
    elif ndvi_value < 0.1:
        return "Bare Soil", "Desert, sand, or areas with almost no vegetation"
    elif ndvi_value < 0.2:
        return "Sparse Vegetation", "Very little plant life, possibly drought or early growth"
    elif ndvi_value < 0.4:
        return "Moderate Vegetation", "Grasslands, shrubs, or crops in early growth stage"
    elif ndvi_value < 0.6:
        return "Healthy Vegetation", "Good plant health, crops in growth phase"
    elif ndvi_value < 0.8:
        return "Dense Vegetation", "Very healthy plants, forests or mature crops"
    else:
        return "Very Dense Vegetation", "Extremely healthy vegetation, likely forests"


def get_vegetation_health_status(mean_ndvi, trend):
    """Get overall vegetation health status"""
    if mean_ndvi < 0.1:
        return "Non-vegetated/Bare Area", "Very low NDVI suggests desert, sand, rock, or water"
    elif mean_ndvi < 0.3:
        if trend > 0.01:
            return "Improving", "Vegetation is getting healthier over time"
        elif trend < -0.01:
            return "Declining", "Vegetation health is decreasing"
        else:
            return "Stable", "Vegetation health is consistent"
    elif mean_ndvi < 0.6:
        if trend > 0.01:
            return "Growing", "Vegetation is actively growing"
        elif trend < -0.01:
            return "Stressed", "Vegetation may be under stress"
        else:
            return "Healthy", "Vegetation is in good condition"
    else:
        if trend > 0.01:
            return "Thriving", "Vegetation is thriving and very healthy"
        elif trend < -0.01:
            return "Peak Declining", "Vegetation may be past peak health"
        else:
            return "Peak Health", "Vegetation is at peak health"


# -------------------- Recommendations --------------------

def get_seasonal_recommendations(month, ndvi_value):
    """Get seasonal recommendations based on month and NDVI"""
    recommendations = []
    if month in [12, 1, 2]:
        recommendations.append("Winter dormancy" if ndvi_value < 0.3 else "Unusual winter growth")
    elif month in [3, 4, 5]:
        recommendations.append("Early spring growth" if ndvi_value < 0.4 else "Active spring growth")
    elif month in [6, 7, 8]:
        recommendations.append("Summer stress" if ndvi_value < 0.5 else "Peak summer growth")
    else:
        recommendations.append("Fall dormancy" if ndvi_value < 0.4 else "Extended growing season")
    return recommendations


def get_management_recommendations(ndvi_value, trend, season):
    """Get actionable management recommendations"""
    recommendations = []
    if ndvi_value < 0.2:
        recommendations += ["Consider soil improvement or irrigation", "Check for pest or disease issues"]
    elif ndvi_value < 0.4:
        recommendations += ["Monitor plant health closely", "Consider fertilization if appropriate"]
    elif ndvi_value < 0.6:
        recommendations += ["Good plant health - maintain current practices", "Monitor for any changes"]
    else:
        recommendations += ["Excellent plant health - continue current management", "Consider harvesting if ready"]

    if trend < -0.02:
        recommendations.append("URGENT: Vegetation health declining - investigate causes")
    elif trend > 0.02:
        recommendations.append("Positive trend - continue current management")

    return recommendations


# -------------------- Reports --------------------

def generate_user_report(df, forecast_dates=None, forecast_values=None, peaks=None):
    """Generate a comprehensive user-friendly report"""
    report = {"summary": {}, "current_status": {}, "trends": {}, "recommendations": {}, "forecast": {}, "peaks": {}}

    mean_ndvi = float(df['NDVI'].mean())
    max_ndvi = float(df['NDVI'].max())
    min_ndvi = float(df['NDVI'].min())
    trend = float((df['NDVI'].iloc[-1] - df['NDVI'].iloc[0]) / len(df)) if len(df) > 1 else 0
    current_ndvi = float(df['NDVI'].iloc[-1])
    current_date = df['Date'].iloc[-1]
    current_month = current_date.month

    veg_type, veg_desc = interpret_ndvi_value(current_ndvi)
    health_status, health_desc = get_vegetation_health_status(mean_ndvi, trend)
    seasonal_recs = get_seasonal_recommendations(current_month, current_ndvi)
    management_recs = get_management_recommendations(current_ndvi, trend, current_month)

    report["summary"] = {
        "analysis_period": f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} to {df['Date'].iloc[-1].strftime('%Y-%m-%d')}",
        "data_points": len(df)
    }

    report["current_status"] = {
        "vegetation_type": veg_type,
        "description": veg_desc,
        "health_status": health_status,
        "health_description": health_desc,
        "current_ndvi": round(current_ndvi, 3),
        "date": current_date.strftime('%Y-%m-%d')
    }

    report["trends"] = {
        "mean_ndvi": round(mean_ndvi, 3),
        "max_ndvi": round(max_ndvi, 3),
        "min_ndvi": round(min_ndvi, 3),
        "trend_direction": "Improving" if trend > 0.01 else "Declining" if trend < -0.01 else "Stable",
        "trend_value": round(trend, 4)
    }

    report["recommendations"] = {"seasonal": seasonal_recs, "management": management_recs}

    if forecast_dates and forecast_values:
        forecast_mean = float(np.mean(forecast_values))
        forecast_trend_val = float((forecast_values[-1] - forecast_values[0]) / len(forecast_values))
        report["forecast"] = {
            "forecast_period": f"{forecast_dates[0].strftime('%Y-%m-%d')} to {forecast_dates[-1].strftime('%Y-%m-%d')}",
            "predicted_mean_ndvi": round(forecast_mean, 3),
            "forecast_trend": "Improving" if forecast_trend_val > 0.01 else "Declining" if forecast_trend_val < -0.01 else "Stable",
            "forecast_interpretation": interpret_ndvi_value(forecast_mean)[0]
        }

    if peaks:
        peak_dates = [df['Date'].iloc[p].strftime('%Y-%m-%d') for p in peaks]
        peak_ndvi_values = [round(float(df['NDVI'].iloc[p]), 3) for p in peaks]
        report["peaks"] = {"total_peaks": len(peaks), "peak_dates": peak_dates, "peak_ndvi_values": peak_ndvi_values}

    return report


def format_user_friendly_output(report):
    """Format the report into readable text"""
    output = ["BLOOMWATCH ANALYSIS REPORT", "=" * 50]
    output += [f"\nANALYSIS SUMMARY", f"Period: {report['summary']['analysis_period']}", f"Data Points: {report['summary']['data_points']}"]
    output += [f"\nCURRENT VEGETATION STATUS", f"Type: {report['current_status']['vegetation_type']}", f"Description: {report['current_status']['description']}",
               f"Health: {report['current_status']['health_status']}", f"Details: {report['current_status']['health_description']}",
               f"Current NDVI: {report['current_status']['current_ndvi']}"]
    output += [f"\nTREND ANALYSIS", f"Average NDVI: {report['trends']['mean_ndvi']}", f"Highest NDVI: {report['trends']['max_ndvi']}",
               f"Lowest NDVI: {report['trends']['min_ndvi']}", f"Trend: {report['trends']['trend_direction']} ({report['trends']['trend_value']})"]
    output += ["\nRECOMMENDATIONS", "Seasonal:"] + [f"  - {r}" for r in report['recommendations']['seasonal']]
    output += ["Management:"] + [f"  - {r}" for r in report['recommendations']['management']]

    if report.get('forecast'):
        f = report['forecast']
        output += [f"\nFORECAST", f"Period: {f['forecast_period']}", f"Predicted NDVI: {f['predicted_mean_ndvi']}",
                   f"Forecast Trend: {f['forecast_trend']}", f"Interpretation: {f['forecast_interpretation']}"]

    if report.get('peaks') and report['peaks'].get('total_peaks', 0) > 0:
        output += [f"\nDETECTED BLOOM EVENTS", f"Total Peaks: {report['peaks']['total_peaks']}"]
        for i, (d, v) in enumerate(zip(report['peaks']['peak_dates'], report['peaks']['peak_ndvi_values'])):
            output.append(f"  Peak {i+1}: {d} (NDVI: {v})")

    return "\n".join(output)
