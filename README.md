# BloomWatch

Satellite-Based Vegetation Monitoring & Bloom Event Analysis

---

## Overview

BloomWatch is a full-stack web application designed to monitor vegetation health and detect bloom events using satellite-derived **NDVI (Normalized Difference Vegetation Index)** data.

The platform enables users to analyze historical vegetation trends for any location on Earth through an interactive map and time-series analytics. It is built for applications in agriculture, environmental monitoring, and ecological research.

The backend leverages **Google Earth Engine (GEE)** for large-scale satellite data processing, while the frontend delivers an intuitive, responsive user experience.

---

## Live Application

The frontend application is deployed and publicly accessible.

The backend API for BloomWatch is deployed on Render.

> Backend services are intentionally kept private and are not exposed publicly.  
> The frontend communicates with the backend through secure configuration, following standard production best practices for API security and access control.

---

## Features

- Global NDVI analysis using satellite imagery  
- Interactive map with region-of-interest (ROI) visualization  
- NDVI time-series charts  
- Bloom event detection using peak analysis  
- Vegetation health classification  
- Human-readable location names via reverse geocoding  
- Optimized handling of large satellite datasets  

---

## Technology Stack

### Frontend
- React (Vite)
- TypeScript
- Leaflet
- Recharts
- Tailwind CSS

### Backend
- FastAPI (Python)
- Google Earth Engine (GEE)
- NumPy
- Pandas
- SciPy

### Deployment
- Frontend: Vercel
- Backend: Private API service

---

## Data Sources

- **Google Earth Engine**
  - MODIS NDVI satellite products
- **OpenStreetMap Nominatim**
  - Reverse geocoding services
- **CartoDB**
  - Base map tiles

---

## Project Architecture

1. User selects location, date range, and ROI size from the frontend  
2. Frontend sends requests to the backend API  
3. Backend processes satellite data using Google Earth Engine  
4. NDVI values and bloom events are computed server-side  
5. Results are returned and visualized on the frontend  

---

## Running Locally

### Backend Setup

```bash
git clone https://github.com/anmolthakur74/BloomWatch.git
cd BloomWatch
python -m venv bloom_env
.\bloom_env\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn backend.main_gee:app --reload
```

### Frontend Setup
```bash
cd web
npm install
npm run dev
```

**Author**
Anmol Thakur

GitHub: https://github.com/anmolthakur74

