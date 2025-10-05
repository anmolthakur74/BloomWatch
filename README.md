# BloomWatch

**Real-Time Vegetation Monitoring & Bloom Event Prediction**

---

## Overview

BloomWatch is a web-based vegetation monitoring platform that leverages **NASA MODIS and GIBS satellite data** to provide:

- Real-time NDVI (Normalized Difference Vegetation Index) analysis for any location on Earth  
- AI-driven bloom event detection and vegetation health forecasting using **LSTM neural networks**  
- Actionable agricultural and ecological insights to support farmers, researchers, and environmentalists  

Our goal is to **democratize access to satellite vegetation data**, eliminating the need for expensive software or technical expertise. Users can simply input coordinates and date ranges to receive comprehensive vegetation health reports and historical trends.

---

## Features

- Real-time NDVI calculation and visualization  
- Bloom event detection and trend analysis  
- Forecasting of future NDVI and potential bloom events using LSTM  
- Interactive map with location-based insights  
- Synthetic NDVI fallback when real-time data is unavailable  

---

## Data Sources

### NASA Data

| Resource | URL |
|----------|-----|
| NASA MODIS NDVI Data | https://modis.ornl.gov/data.html |
| NASA GIBS (Global Imagery Browse Services) | https://nasa-gibs.github.io/gibs-api-docs/ |
| NASA CMR (Common Metadata Repository) | https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html |
| MODIS Products Overview | https://modis.gsfc.nasa.gov/data/dataprod/ |

### Space Agency Partner & Other Data

| Resource | URL |
|----------|-----|
| OpenStreetMap Nominatim (Geocoding) | https://nominatim.openstreetmap.org/ |
| CartoDB Basemap (Map Tiles) | https://carto.com/ |
| GLOBE Observer Wildflower Bloom Data | https://observer.globe.gov/ |

---

## Installation & Setup

## How to Run Locally

### Backend & Frontend

```bash
# Clone the repository
git clone https://github.com/yourusername/BloomWatch.git
cd BloomWatch

# Create Python virtual environment
python -m venv bloom_env

# Activate virtual environment
# Windows PowerShell
.\bloom_env\Scripts\Activate.ps1
# Windows Command Prompt
# .\bloom_env\Scripts\activate.bat
# macOS / Linux
# source bloom_env/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Start backend server
python start_nasa_api.py --reload

# Frontend setup
cd web
npm install
npm run dev

# Open in a web browser:
# Go to http://localhost:5173 (or the port shown in your terminal)
```

## Contact

**Anmol Thakur** – anmol@example.com

