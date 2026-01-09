import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import dayjs from 'dayjs'
import { MapContainer, ImageOverlay, TileLayer, ZoomControl, Rectangle } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Scatter } from 'recharts'
import { Leaf, MapPin } from 'lucide-react'

type NDVIRecord = { Date: string; NDVI: number }

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const FRONTEND_ONLY = (import.meta.env.VITE_FRONTEND_ONLY || 'false').toLowerCase() === 'true'

export function App() {
  // ---------------- State ----------------
  const [latitude, setLatitude] = useState(37)
  const [longitude, setLongitude] = useState(-120)
  const [latInput, setLatInput] = useState('37')
  const [lonInput, setLonInput] = useState('-120')
  const [roiSize, setRoiSize] = useState(5)
  const [startDate, setStartDate] = useState('2000-01-01')
  const [endDate, setEndDate] = useState(dayjs().format('YYYY-MM-DD'))
  const [threshold, setThreshold] = useState(0.2)

  const [ndvi, setNdvi] = useState<NDVIRecord[]>([])
  const [peaks, setPeaks] = useState<number[]>([])
  const [thumbUrl, setThumbUrl] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [info, setInfo] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [hasResults, setHasResults] = useState(false)
  const [hasRun, setHasRun] = useState(false)
  const [placeName, setPlaceName] = useState<string>('')
  const [locationLoading, setLocationLoading] = useState(false)
  const [roiColor, setRoiColor] = useState<string>('blue')
  const [locationCache, setLocationCache] = useState<Record<string,string>>({})

  // ---------------- Memoized Request Body ----------------
  const requestBody = useMemo(() => ({
    latitude, longitude, roi_size_degrees: roiSize, start_date: startDate, end_date: endDate
  }), [latitude, longitude, roiSize, startDate, endDate])

  // ---------------- Reverse Geocoding ----------------
  async function fetchLocationName(lat: number, lon: number): Promise<string> {
    const key = `${lat},${lon}`
    if(locationCache[key]) return locationCache[key]
    setLocationLoading(true)
    try {
      try {
        const res = await axios.get('https://nominatim.openstreetmap.org/reverse', {
          params: { format: 'jsonv2', lat, lon, zoom: 8, addressdetails: 1, 'accept-language': 'en' },
          timeout: 5000,
          headers: { 'User-Agent': 'BloomWatch/1.0 (Vegetation Monitoring)' }
        })
        const addr = res.data.address
        if(addr) {
          const parts: string[] = []
          if(addr.city) parts.push(addr.city)
          else if(addr.town) parts.push(addr.town)
          else if(addr.village) parts.push(addr.village)
          else if(addr.county) parts.push(addr.county)
          if(addr.state) parts.push(addr.state)
          else if(addr.region) parts.push(addr.region)
          else if(addr.province) parts.push(addr.province)
          if(addr.country) parts.push(addr.country)
          if(parts.length>0) {
            setLocationCache({...locationCache,[key]:parts.join(', ')})
            return parts.join(', ')
          }
        }
      } catch {}
      const fallback = generateFallbackLocation(lat, lon)
      setLocationCache({...locationCache,[key]:fallback})
      return fallback
    } finally { setLocationLoading(false) }
  }

  function generateFallbackLocation(lat: number, lon: number): string {
    const latDir = lat >= 0 ? 'N' : 'S'
    const lonDir = lon >= 0 ? 'E' : 'W'
    const absLat = Math.abs(lat).toFixed(2)
    const absLon = Math.abs(lon).toFixed(2)
    let region = 'Unknown Region'
    if (lat >= 25 && lat <= 50 && lon >= -125 && lon <= -65) region = 'North America'
    else if (lat >= -35 && lat <= 12 && lon >= -80 && lon <= -35) region = 'South America'
    else if (lat >= 35 && lat <= 70 && lon >= -10 && lon <= 40) region = 'Europe'
    else if (lat >= -35 && lat <= 37 && lon >= -18 && lon <= 52) region = 'Africa'
    else if (lat >= -10 && lat <= 55 && lon >= 40 && lon <= 145) region = 'Asia'
    else if (lat >= -45 && lat <= -10 && lon >= 110 && lon <= 155) region = 'Australia/Oceania'
    else if (Math.abs(lon) > 150 || Math.abs(lon) < 30) region = 'Pacific Ocean'
    return `${region} (${absLat}°${latDir}, ${absLon}°${lonDir})`
  }

  // ---------------- Fetch NDVI & Peaks & Analysis ----------------
async function fetchAll() {
  setHasRun(true);       
  setLoading(true);
  setHasResults(false);
  setNdvi([]);
  setPeaks([]);
  setThumbUrl('');
  setAnalysis(null);
  setInfo(null);

  try {
    // ---------------- Get location name ----------------
    const locationName = await fetchLocationName(latitude, longitude);
    setPlaceName(locationName);

    // ---------------- Frontend-only mode ----------------
    if (FRONTEND_ONLY) {
      const gibsUrl = `https://gibs-{s}.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/${dayjs(endDate).format('YYYY-MM-DD')}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`;
      setThumbUrl(gibsUrl);
      setInfo('Frontend-only mode: showing public NDVI tiles. Analytics disabled.');
      setHasResults(true);
      return;
    }

    // ---------------- Format dates for backend ----------------
    const formattedRequestBody = {
      ...requestBody,
      start_date: dayjs(startDate, "DD-MM-YYYY").format("YYYY-MM-DD"),
      end_date: dayjs(endDate, "DD-MM-YYYY").format("YYYY-MM-DD")
    };

    // ---------------- Fetch NDVI ----------------
const ndviRes = await axios.post(`${API_BASE}/api/ndvi`, formattedRequestBody);
const ndviRecords = ndviRes.data.records ?? [];
setNdvi(ndviRecords);

// ---------------- UX clarification for large ROI ----------------
if (roiSize > 5 && ndviRecords.length > 0) {
  setInfo(
    "NDVI values represent the average vegetation over the selected region. " +
    "In uniform areas like oceans, deserts, or ice, changing ROI size may not " +
    "significantly affect NDVI results."
  );
}

// ---------------- Handle no data ----------------
if (ndviRecords.length === 0) {
  setInfo(
    "No NDVI data available for the selected region and date range. " +
    "This can happen if the area has no vegetation (e.g., ocean, desert, ice) " +
    "or if satellite imagery is unavailable."
  );
  setHasResults(false);
  return;
}

    // ---------------- Fetch Peaks ----------------
const peaksRes = await axios.post(`${API_BASE}/api/peaks`, {
  ...formattedRequestBody,
  threshold
});

const detectedPeaks = peaksRes.data.peaks ?? [];
setPeaks(detectedPeaks);

if (ndviRecords.length > 0 && detectedPeaks.length === 0) {
  setInfo(
    "No bloom events exceeded the selected threshold. " +
    "Try lowering the threshold (e.g., 0.3–0.6) to detect seasonal growth patterns."
  );
}


    // ---------------- Fetch Thumbnail ----------------
    await axios
      .post(`${API_BASE}/api/ndvi-thumb`, formattedRequestBody)
      .then(res => {
        if (res.data.url) {
          setThumbUrl(`${res.data.url}${res.data.url.includes('?') ? '&' : '?'}ts=${Date.now()}`);
        }
      })
      .catch(() => {});

    // ---------------- Fetch Analytics ----------------
    try {
      const analysisRes = await axios.post(`${API_BASE}/api/analysis`, { ...formattedRequestBody, threshold });

      if (analysisRes.data.success) {
        setAnalysis(analysisRes.data);
      } else {
        // NO data available is **not a network error**
        setInfo('No NDVI data available for the selected region and date range.');
      }
    } catch {
      // ONLY true network/server errors
      // You can comment this line if you want to hide the message completely
      // setInfo('Network or server error: Failed to load analytics.');
    }

    setHasResults(true);
  } catch (e: any) {
    // This is only for fatal/unexpected errors
    console.error(e);
    // setInfo(`Network or server error: ${e?.message || "Failed to load data"}`);
  } finally {
    setLoading(false);
  }
}

  // ---------------- Chart Data ----------------
  const combinedSeries = useMemo(() => ndvi.map(r=>({date:r.Date.substring(0,10), historical:r.NDVI})), [ndvi])

  const peakPoints = useMemo(() => peaks.map(idx => {
    const rec = ndvi[idx]
    return rec ? {date: rec.Date.substring(0,10), peak: rec.NDVI} : null
  }).filter(Boolean) as {date:string; peak:number}[], [ndvi, peaks])

  // ---------------- ROI Color ----------------
  useEffect(() => {
    if(!hasResults || ndvi.length===0) return
    const latest = ndvi[ndvi.length-1].NDVI
    if(latest>=0.7) setRoiColor('#006400')
    else if(latest>=0.6) setRoiColor('#228B22')
    else if(latest>=0.4) setRoiColor('#32CD32')
    else if(latest>=0.2) setRoiColor('#ADFF2F')
    else if(latest>=0.1) setRoiColor('#FFFF00')
    else setRoiColor('#00BFFF')
  }, [ndvi, hasResults])

  // ---------------- JSX ----------------
  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white">
      <header className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-brand to-brand-light opacity-10" />
        <div className="max-w-7xl mx-auto px-6 py-8 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-brand text-white grid place-items-center shadow"><Leaf size={22}/></div>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">BloomWatch</h1>
            <p className="text-sm text-gray-600">MODIS NDVI Viewer & Analytics</p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Settings */}
        <section className="card glass p-5 lg:col-span-1">
          <h2 className="text-lg font-medium mb-4">Settings</h2>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm text-gray-600">Latitude
              <input type="text" inputMode="decimal" className="mt-1 w-full border rounded px-2 py-1"
                value={latInput} onChange={e=>{setLatInput(e.target.value); const n=Number(e.target.value); if(!Number.isNaN(n)) setLatitude(Math.max(-90,Math.min(90,n)))}}
                onBlur={()=>{ const n=Number(latInput); const safe=Number.isNaN(n)?latitude:Math.max(-90,Math.min(90,n)); setLatitude(safe); setLatInput(String(safe)) }} placeholder="e.g. -15.5"/>
            </label>
            <label className="text-sm text-gray-600">Longitude
              <input type="text" inputMode="decimal" className="mt-1 w-full border rounded px-2 py-1"
                value={lonInput} onChange={e=>{setLonInput(e.target.value); const n=Number(e.target.value); if(!Number.isNaN(n)) setLongitude(Math.max(-180,Math.min(180,n)))}}
                onBlur={()=>{ const n=Number(lonInput); const safe=Number.isNaN(n)?longitude:Math.max(-180,Math.min(180,n)); setLongitude(safe); setLonInput(String(safe)) }} placeholder="e.g. 30"/>
            </label>
            <label className="text-sm text-gray-600">
  ROI Size (deg)
  <input
    type="number"
    step="0.1"
    min="0.1"
    className="mt-1 w-full border rounded px-2 py-1"
    value={roiSize}
    onChange={e => {
      const v = Math.max(0.1, parseFloat(e.target.value))
      setRoiSize(v)
    }}
  />
</label>
            <label className="text-sm text-gray-600">Start Date<input type="date" className="mt-1 w-full border rounded px-2 py-1" value={startDate} onChange={e=>setStartDate(e.target.value)}/></label>
            <label className="text-sm text-gray-600">End Date<input type="date" className="mt-1 w-full border rounded px-2 py-1" value={endDate} onChange={e=>setEndDate(e.target.value)}/></label>
            <label className="text-sm text-gray-600">
  Bloom Threshold
  <input
    type="number"
    min={0.1}
    max={1}
    step="0.01"
    className="mt-1 w-full border rounded px-2 py-1"
    value={threshold}
    onChange={e => {
      const v = parseFloat(e.target.value)
      if (!Number.isNaN(v)) {
        setThreshold(Math.max(0.1, Math.min(1, v)))
      }
    }}
  />
</label>

          </div>
          <div className="mt-4"><button className="btn-primary w-full" onClick={fetchAll} disabled={loading}>{loading?'Loading…':'Run'}</button></div>
          {info && <p className="mt-3 text-sm text-blue-700">{info}</p>}
        </section>

        {/* Map */}
        <section className="card glass p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">NDVI Map</h2>
            <div className="flex items-center gap-2 flex-wrap">
              {placeName && <span className="badge flex items-center gap-1"><MapPin size={12}/>{locationLoading?'Locating...':placeName}</span>}
              <span className="badge">ROI {roiSize.toFixed(1)}°</span>
              <span className="badge">Detected Peaks {peaks?.length||0}</span>
            </div>
          </div>
          <div className="h-80 overflow-hidden rounded-lg border-2 border-gray-200">
            <MapContainer key={`${latitude},${longitude},${roiSize}`} center={[latitude,longitude]} zoom={6} zoomControl={false} style={{height:'100%',width:'100%'}}>
              <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" attribution='&copy; OpenStreetMap contributors &copy; CARTO'/>
              <ZoomControl position="topright" zoomInTitle="Zoom in" zoomOutTitle="Zoom out"/>
              {hasResults && thumbUrl && <ImageOverlay url={thumbUrl} bounds={[[latitude-roiSize/2,longitude-roiSize/2],[latitude+roiSize/2,longitude+roiSize/2]]} opacity={0.85} interactive={false}/>}
              {hasResults && ndvi.length>0 && <Rectangle bounds={[[latitude-roiSize/2,longitude-roiSize/2],[latitude+roiSize/2,longitude+roiSize/2]]} pathOptions={{color:roiColor,fillColor:roiColor,fillOpacity:0.35}} interactive={false}/>}
            </MapContainer>
          </div>
        </section>

        {/* Time Series Chart */}
        <section className="card glass p-5 lg:col-span-3">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">NDVI Time Series</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={combinedSeries} margin={{top:5,right:20,bottom:5,left:0}}>
                <CartesianGrid stroke="#eee" strokeDasharray="5 5"/>
                <XAxis dataKey="date" minTickGap={20}/>
                <YAxis domain={[-0.1,1]}/>
                <Tooltip/>
                <Legend/>
                <Line type="monotone" dataKey="historical" stroke="#1f77b4" dot={false} name="NDVI"/>
                {peakPoints.length>0 && <Scatter data={peakPoints} dataKey="peak" name="NDVI Peaks" fill="#e11d48" shape="circle"/>}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        
        {/* NDVI Analytics / Report */}
{!hasRun ? (
  // Case 1: User hasn't run anything yet
  <section className="lg:col-span-3">
    <p className="text-gray-500 text-center py-6">
      Select a region and click <strong>Run</strong> to view NDVI data.
    </p>
  </section>
) : ndvi.length === 0 ? (
  // Case 2: User ran but no NDVI data found
  <section className="lg:col-span-3">
    <p className="text-gray-600 text-center py-6">
      No NDVI data available for the selected region and date range.<br />
      This can happen if the area has no vegetation (e.g., ocean, desert, ice)<br />
      or if satellite imagery is unavailable for the selected dates.
    </p>
  </section>
) : analysis?.report ? (
  // Case 3: Analysis available, show report
  <section className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-6">
    
    {/* Summary Card */}
    <div className="card glass p-5 shadow-sm">
      <h3 className="font-semibold text-lg mb-3">Summary</h3>
      <p><span className="font-medium">Analysis Period:</span> {analysis.report.summary?.analysis_period ?? 'N/A'}</p>
      <p><span className="font-medium">Data Points:</span> {analysis.report.summary?.data_points ?? 0}</p>
    </div>

    {/* Current Status Card */}
<div className="card glass p-5 shadow-sm">
  <h3 className="font-semibold text-lg mb-3">Current Vegetation Status</h3>

  {/* Vegetation Type */}
  <p>
    <span className="font-medium">Vegetation Type:</span>{' '}
    {analysis.report.current_status?.vegetation_type ?? 'N/A'}
  </p>

  {/* Health Status */}
  <p>
    <span className="font-medium">Health Status:</span>{' '}
    <span
      className={`ml-2 px-2 py-0.5 rounded text-white ${
        {
          "Non-vegetated/Bare Area": "bg-gray-500",
          "Improving": "bg-green-500",
          "Growing": "bg-green-500",
          "Healthy": "bg-green-700",
          "Thriving": "bg-green-700",
          "Peak Health": "bg-green-700",
          "Stable": "bg-yellow-500",
          "Declining": "bg-red-600",
          "Stressed": "bg-orange-600",
          "Peak Declining": "bg-red-600"
        }[analysis.report.current_status?.health_status ?? ""] || "bg-gray-400"
      }`}
    >
      {analysis.report.current_status?.health_status ?? 'N/A'}
    </span>
  </p>

  {/* Current NDVI */}
  <p>
    <span className="font-medium">Current NDVI:</span>{' '}
    {analysis.report.current_status?.current_ndvi !== undefined
      ? analysis.report.current_status.current_ndvi.toFixed(3)
      : 'N/A'}
  </p>

  {/* Date */}
  <p>
    <span className="font-medium">Date:</span>{' '}
    {analysis.report.current_status?.date ?? 'N/A'}
  </p>
</div>

  {/* Current NDVI */}
  <p>
    <span className="font-medium">Current NDVI:</span>{' '}
    <span className={`ml-2 px-2 py-0.5 rounded text-white ${
      analysis.report.current_status?.current_ndvi !== undefined
        ? analysis.report.current_status.current_ndvi >= 0.7
          ? 'bg-green-700'
          : analysis.report.current_status.current_ndvi >= 0.4
          ? 'bg-green-500'
          : analysis.report.current_status.current_ndvi >= 0.2
          ? 'bg-yellow-500'
          : 'bg-red-600'
        : 'bg-gray-400'
    }`}>
      {analysis.report.current_status?.current_ndvi !== undefined
        ? analysis.report.current_status.current_ndvi.toFixed(3)
        : 'N/A'}
    </span>
  </p>

  {/* Date */}
  <p>
    <span className="font-medium">Date:</span>{' '}
    {analysis.report.current_status?.date ?? 'N/A'}
  </p>
</div>

    {/* Trends Card */}
    <div className="card glass p-5 shadow-sm">
      <h3 className="font-semibold text-lg mb-3">Trends</h3>
      <p><span className="font-medium">Mean NDVI:</span> {analysis.report.trends?.mean_ndvi ?? 'N/A'}</p>
      <p><span className="font-medium">Trend Value:</span> {analysis.report.trends?.trend_value ?? 'N/A'}</p>
      <p>
        <span className="font-medium">Trend Direction:</span>{' '}
        <span className={`ml-2 px-2 py-0.5 rounded text-white ${
          analysis.report.trends?.trend_direction === 'Improving' ? 'bg-green-600' :
          analysis.report.trends?.trend_direction === 'Declining' ? 'bg-red-600' : 'bg-yellow-500'
        }`}>
          {analysis.report.trends?.trend_direction ?? 'N/A'}
        </span>
      </p>
    </div>

    {/* Recommendations Card */}
    <div className="card glass p-5 shadow-sm space-y-3">
      <h3 className="font-semibold text-lg mb-2">Recommendations</h3>
      <div>
        <p className="font-medium">Seasonal:</p>
        <ul className="list-disc ml-5">
          {analysis.report.recommendations?.seasonal?.length
            ? analysis.report.recommendations.seasonal.map((rec: string, i: number) => <li key={i}>{rec}</li>)
            : <li>N/A</li>}
        </ul>
      </div>
      <div>
        <p className="font-medium mt-2">Management:</p>
        <ul className="list-disc ml-5">
          {analysis.report.recommendations?.management?.length
            ? analysis.report.recommendations.management.map((rec: string, i: number) => <li key={i}>{rec}</li>)
            : <li>N/A</li>}
        </ul>
      </div>
    </div>

    {/* Bloom Peaks Table Card */}
    {analysis.report.peaks?.total_peaks > 0 && (
      <div className="card glass p-5 shadow-sm md:col-span-2">
        <h3 className="font-semibold text-lg mb-3">Detected Bloom Events ({analysis.report.peaks.total_peaks})</h3>
        <div className="overflow-x-auto max-h-64 border-t border-gray-200 pt-2">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-3 py-2">Serial No.</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">NDVI</th>
              </tr>
            </thead>
            <tbody>
              {analysis.report.peaks.peak_dates.map((date: string, i: number) => (
                <tr key={i} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="px-3 py-2">{i + 1}</td>
                  <td className="px-3 py-2">{date}</td>
                  <td className="px-3 py-2">{analysis.report.peaks.peak_ndvi_values[i]?.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )}

  </section>
) : null /* Case 4: fallback, render nothing if none of the above */}


      </main>
    </div>
  )
}





