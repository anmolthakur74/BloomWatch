BloomWatch (FastAPI + React)

Tech Stack

- Backend: FastAPI, Uvicorn, Pandas, NumPy, SciPy, Requests
  - Data sources: NASA MODIS/GIBS (tiles/thumbnail), NASA ORNL MODIS Subset (MOD13C1 time series)
- Frontend: React (Vite), TypeScript, Tailwind CSS, Leaflet, Recharts, dayjs, axios, lucide-react

How to Run

Backend (Terminal 1 in VS Code)

1. "python -m venv bloom_env"
2. `.\bloom_env\Scripts\Activate.ps1`
3. `pip install -r requirements.txt`
4. `python start_nasa_api.py --reload`

Frontend (Terminal 2 in VS Code)

1. `cd web`
2. `npm install`
3. `npm run dev`

