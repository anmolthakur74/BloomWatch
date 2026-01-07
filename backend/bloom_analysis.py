"""
bloom_analysis.py
Utility functions for analyzing bloom events using NASA MODIS NDVI data
"""

import pandas as pd
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None
from scipy.signal import find_peaks
import numpy as np

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def plot_ndvi_timeseries(df):
    """
    Plot NDVI time series
    """
    if df.empty:
        return None
    if plt is None:
        return None

    fig, ax = plt.subplots(figsize=(12,5))
    ax.plot(df['Date'], df['NDVI'], linestyle='-', color="blue", alpha=0.7, label="NDVI")

    if len(df) > 10:
        df['NDVI_smooth'] = df['NDVI'].rolling(window=5, center=True).mean()
        ax.plot(df['Date'], df['NDVI_smooth'], color="red", linewidth=2, label="Smoothed NDVI")

    ax.set_title("NDVI Time Series (Scaled 0-1)")
    ax.set_xlabel("Date")
    ax.set_ylabel("NDVI")
    ax.set_ylim(-0.1, 1.0)
    ax.legend()
    ax.grid(True)
    return fig


def detect_bloom_peaks(df, threshold=0.2):
    """
    Detect bloom peaks in NDVI data
    """
    if df.empty:
        return [], {}

    ndvi_series = df['NDVI'].values
    peaks, props = find_peaks(ndvi_series, height=threshold)

    if plt is not None:
        fig, ax = plt.subplots(figsize=(12,5))
        ax.plot(df['Date'], ndvi_series, color="blue", label="NDVI")
        ax.plot(df['Date'].iloc[peaks], ndvi_series[peaks], "rx", label="Bloom Peaks")
        ax.legend()
        ax.set_title("Detected Bloom Events")
        ax.set_xlabel("Date")
        ax.set_ylabel("NDVI")
        ax.set_ylim(-0.1, 1.0)
        ax.grid(True)
        plt.show()

    return peaks, props


def lstm_forecast(df, future_steps=60, look_back=30, anchor_end_date: str | None = None):
    """
    LSTM forecasting with fixed date boundary issues
    """
    if df.empty:
        return None, None

    if df["NDVI"].mean() < 0.05:
        return None, None

    scaler = MinMaxScaler(feature_range=(0, 1))
    dataset = scaler.fit_transform(df[['NDVI']].values)

    if len(dataset) <= look_back + 5:
        look_back = max(5, len(dataset) // 3)

    train_size = int(len(dataset) * 0.8)
    train, test = dataset[:train_size], dataset[train_size:]

    def create_sequences(data, look_back):
        X, y = [], []
        for i in range(len(data) - look_back):
            X.append(data[i:i+look_back, 0])
            y.append(data[i+look_back, 0])
        return np.array(X), np.array(y)

    X_train, y_train = create_sequences(train, look_back)
    X_test, y_test = create_sequences(test, look_back)

    if X_test.size == 0 or y_test.size == 0:
        X_test, y_test = None, None

    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
    if X_test is not None:
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

    model = Sequential()
    model.add(LSTM(32, return_sequences=True, input_shape=(look_back, 1), name="lstm_1"))
    model.add(Dropout(0.15, name="dropout_1"))
    model.add(LSTM(32, return_sequences=False, name="lstm_2"))
    model.add(Dropout(0.15, name="dropout_2"))
    model.add(Dense(1, name="output"))
    model.compile(optimizer="adam", loss="mean_squared_error")

    model.fit(X_train, y_train, epochs=8, batch_size=32, verbose=0)

    if X_test is not None:
        y_pred = model.predict(X_test, verbose=0)
        y_pred = scaler.inverse_transform(y_pred)
        y_test_rescaled = scaler.inverse_transform(y_test.reshape(-1, 1))

        rmse = np.sqrt(mean_squared_error(y_test_rescaled, y_pred))
        mae = mean_absolute_error(y_test_rescaled, y_pred)
        r2 = r2_score(y_test_rescaled, y_pred)

    last_seq = dataset[-look_back:]
    future_preds = []
    current_seq = last_seq.reshape(1, look_back, 1)

    for _ in range(future_steps):
        next_pred = model.predict(current_seq, verbose=0)[0][0]
        future_preds.append(next_pred)
        current_seq = np.append(current_seq[:, 1:, :], [[[next_pred]]], axis=1)

    future_preds = scaler.inverse_transform(np.array(future_preds).reshape(-1, 1))

    # FIX: Forecast should start AFTER last historical date
    if anchor_end_date is not None:
        end_dt = pd.to_datetime(anchor_end_date)
        start_dt = end_dt + pd.Timedelta(days=1)
    else:
        last_date = df["Date"].iloc[-1]
        start_dt = last_date + pd.Timedelta(days=1)
    
    future_dates = pd.date_range(start=start_dt, periods=future_steps)

    return future_dates, future_preds.flatten()


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


def get_seasonal_recommendations(month, ndvi_value):
    """Get seasonal recommendations based on month and NDVI"""
    recommendations = []
    
    if month in [12, 1, 2]:
        if ndvi_value < 0.3:
            recommendations.append("Winter dormancy - normal for most plants")
        else:
            recommendations.append("Unusual winter growth - check for evergreen species")
    elif month in [3, 4, 5]:
        if ndvi_value < 0.4:
            recommendations.append("Early spring - plants may be starting to grow")
        else:
            recommendations.append("Active spring growth - good time for planting")
    elif month in [6, 7, 8]:
        if ndvi_value < 0.5:
            recommendations.append("Summer stress - may need irrigation")
        else:
            recommendations.append("Peak summer growth - monitor for drought")
    else:
        if ndvi_value < 0.4:
            recommendations.append("Fall dormancy - normal seasonal decline")
        else:
            recommendations.append("Extended growing season - monitor for frost")
    
    return recommendations


def get_management_recommendations(ndvi_value, trend, season):
    """Get actionable management recommendations"""
    recommendations = []
    
    if ndvi_value < 0.2:
        recommendations.append("Consider soil improvement or irrigation")
        recommendations.append("Check for pest or disease issues")
    elif ndvi_value < 0.4:
        recommendations.append("Monitor plant health closely")
        recommendations.append("Consider fertilization if appropriate")
    elif ndvi_value < 0.6:
        recommendations.append("Good plant health - maintain current practices")
        recommendations.append("Monitor for any changes")
    else:
        recommendations.append("Excellent plant health - continue current management")
        recommendations.append("Consider harvesting if crops are ready")
    
    if trend < -0.02:
        recommendations.append("URGENT: Vegetation health declining - investigate causes")
    elif trend > 0.02:
        recommendations.append("Positive trend - continue current management")
    
    return recommendations


def generate_user_report(df, forecast_dates=None, forecast_values=None, peaks=None):
    """Generate a comprehensive user-friendly report"""
    report = {
        "summary": {},
        "current_status": {},
        "trends": {},
        "recommendations": {},
        "forecast": {},
        "peaks": {}
    }
    
    mean_ndvi = df['NDVI'].mean()
    max_ndvi = df['NDVI'].max()
    min_ndvi = df['NDVI'].min()
    
    if len(df) > 1:
        trend = (df['NDVI'].iloc[-1] - df['NDVI'].iloc[0]) / len(df)
    else:
        trend = 0
    
    current_ndvi = df['NDVI'].iloc[-1]
    current_date = df['Date'].iloc[-1]
    current_month = current_date.month
    
    vegetation_type, description = interpret_ndvi_value(current_ndvi)
    health_status, health_description = get_vegetation_health_status(mean_ndvi, trend)
    
    report["summary"] = {
        "analysis_period": f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} to {df['Date'].iloc[-1].strftime('%Y-%m-%d')}",
        "data_points": len(df)
    }
    
    report["current_status"] = {
        "vegetation_type": vegetation_type,
        "description": description,
        "health_status": health_status,
        "health_description": health_description,
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
    
    seasonal_recs = get_seasonal_recommendations(current_month, current_ndvi)
    management_recs = get_management_recommendations(current_ndvi, trend, current_month)
    
    report["recommendations"] = {
        "seasonal": seasonal_recs,
        "management": management_recs
    }
    
    if forecast_dates is not None and forecast_values is not None:
        forecast_mean = np.mean(forecast_values)
        forecast_trend = (forecast_values[-1] - forecast_values[0]) / len(forecast_values)
        
        report["forecast"] = {
            "forecast_period": f"{forecast_dates[0].strftime('%Y-%m-%d')} to {forecast_dates[-1].strftime('%Y-%m-%d')}",
            "predicted_mean_ndvi": round(forecast_mean, 3),
            "forecast_trend": "Improving" if forecast_trend > 0.01 else "Declining" if forecast_trend < -0.01 else "Stable",
            "forecast_interpretation": interpret_ndvi_value(forecast_mean)[0]
        }
    
    if peaks is not None and len(peaks) > 0:
        peak_dates = [df['Date'].iloc[peak].strftime('%Y-%m-%d') for peak in peaks]
        peak_ndvi_values = [round(df['NDVI'].iloc[peak], 3) for peak in peaks]
        
        report["peaks"] = {
            "total_peaks": len(peaks),
            "peak_dates": peak_dates,
            "peak_ndvi_values": peak_ndvi_values
        }
    
    return report


def format_user_friendly_output(report):
    """Format the report into a user-friendly text output"""
    output = []
    output.append("BLOOMWATCH ANALYSIS REPORT")
    output.append("=" * 50)
    
    output.append(f"\nANALYSIS SUMMARY")
    output.append(f"Period: {report['summary']['analysis_period']}")
    output.append(f"Data Points: {report['summary']['data_points']}")
    
    output.append(f"\nCURRENT VEGETATION STATUS")
    output.append(f"Type: {report['current_status']['vegetation_type']}")
    output.append(f"Description: {report['current_status']['description']}")
    output.append(f"Health: {report['current_status']['health_status']}")
    output.append(f"Details: {report['current_status']['health_description']}")
    output.append(f"Current NDVI: {report['current_status']['current_ndvi']}")
    
    output.append(f"\nTREND ANALYSIS")
    output.append(f"Average NDVI: {report['trends']['mean_ndvi']}")
    output.append(f"Highest NDVI: {report['trends']['max_ndvi']}")
    output.append(f"Lowest NDVI: {report['trends']['min_ndvi']}")
    output.append(f"Trend: {report['trends']['trend_direction']} ({report['trends']['trend_value']})")
    
    output.append(f"\nRECOMMENDATIONS")
    output.append("Seasonal:")
    for rec in report['recommendations']['seasonal']:
        output.append(f"  - {rec}")
    output.append("Management:")
    for rec in report['recommendations']['management']:
        output.append(f"  - {rec}")
    
    if report['forecast']:
        output.append(f"\nFORECAST")
        output.append(f"Period: {report['forecast']['forecast_period']}")
        output.append(f"Predicted NDVI: {report['forecast']['predicted_mean_ndvi']}")
        output.append(f"Forecast Trend: {report['forecast']['forecast_trend']}")
        output.append(f"Interpretation: {report['forecast']['forecast_interpretation']}")
    
    if report['peaks'] and report['peaks']['total_peaks'] > 0:
        output.append(f"\nDETECTED BLOOM EVENTS")
        output.append(f"Total Peaks: {report['peaks']['total_peaks']}")
        for i, (date, ndvi) in enumerate(zip(report['peaks']['peak_dates'], report['peaks']['peak_ndvi_values'])):
            output.append(f"  Peak {i+1}: {date} (NDVI: {ndvi})")
    
    return "\n".join(output)
