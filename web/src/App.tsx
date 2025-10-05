import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import dayjs from 'dayjs'
import { MapContainer, ImageOverlay, TileLayer, ZoomControl, Rectangle } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Scatter, ScatterChart } from 'recharts'
import { Leaf, MapPin } from 'lucide-react'

type NDVIRecord = { Date: string; NDVI: number }

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const FRONTEND_ONLY = (import.meta.env.VITE_FRONTEND_ONLY || 'false').toLowerCase() === 'true'

export function App() {
  const [latitude, setLatitude] = useState(37)
  const [longitude, setLongitude] = useState(-120)
  const [latInput, setLatInput] = useState('37')
  const [lonInput, setLonInput] = useState('-120')
  const [roiSize, setRoiSize] = useState(5)
  const [startDate, setStartDate] = useState('2000-01-01')
  const [endDate, setEndDate] = useState(dayjs().format('YYYY-MM-DD'))
  const [threshold, setThreshold] = useState(0.2)
  const [futureSteps, setFutureSteps] = useState(60)
  const dataSource = 'nasa'

  const [ndvi, setNdvi] = useState<NDVIRecord[]>([])
  const [peaks, setPeaks] = useState<number[]>([])
  const [forecastDates, setForecastDates] = useState<string[]>([])
  const [forecastValues, setForecastValues] = useState<number[]>([])
  const [thumbUrl, setThumbUrl] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [lastFetchTime, setLastFetchTime] = useState<number>(0)
  const [info, setInfo] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [hasResults, setHasResults] = useState(false)
  const [placeName, setPlaceName] = useState<string>('')
  const [locationLoading, setLocationLoading] = useState(false)

  const requestBody = useMemo(() => ({
    latitude, longitude, roi_size_degrees: roiSize, start_date: startDate, end_date: endDate, data_source: 'nasa'
  }), [latitude, longitude, roiSize, startDate, endDate])

  // Improved reverse geocoding with multiple fallbacks
  async function fetchLocationName(lat: number, lon: number): Promise<string> {
    setLocationLoading(true)
    try {
      // Primary: Nominatim with better error handling
      try {
        const res = await axios.get('https://nominatim.openstreetmap.org/reverse', {
          params: {
            format: 'jsonv2',
            lat: lat,
            lon: lon,
            zoom: 8,
            addressdetails: 1,
            'accept-language': 'en'
          },
          timeout: 5000,
          headers: {
            'User-Agent': 'BloomWatch/1.0 (Vegetation Monitoring)'
          }
        })

        if (res.data && res.data.address) {
          const addr = res.data.address
          const display = res.data.display_name
          
          const parts = []
          
          if (addr.city) parts.push(addr.city)
          else if (addr.town) parts.push(addr.town)
          else if (addr.village) parts.push(addr.village)
          else if (addr.county) parts.push(addr.county)
          
          if (addr.state) parts.push(addr.state)
          else if (addr.region) parts.push(addr.region)
          else if (addr.province) parts.push(addr.province)
          
          if (addr.country) parts.push(addr.country)
          
          if (parts.length > 0) {
            return parts.join(', ')
          }
          
          if (display) {
            const simplified = display.split(',').slice(0, 3).join(',')
            return simplified
          }
        }
      } catch (nominatimError) {
        console.warn('Nominatim failed:', nominatimError)
      }

      return generateFallbackLocation(lat, lon)

    } catch (error) {
      console.error('All geocoding methods failed:', error)
      return generateFallbackLocation(lat, lon)
    } finally {
      setLocationLoading(false)
    }
  }

  function generateFallbackLocation(lat: number, lon: number): string {
    const latDir = lat >= 0 ? 'N' : 'S'
    const lonDir = lon >= 0 ? 'E' : 'W'
    const absLat = Math.abs(lat).toFixed(2)
    const absLon = Math.abs(lon).toFixed(2)

    let region = 'Unknown Region'
    
    if (lat >= 25 && lat <= 50 && lon >= -125 && lon <= -65) {
      region = 'North America'
    } else if (lat >= -35 && lat <= 12 && lon >= -80 && lon <= -35) {
      region = 'South America'
    } else if (lat >= 35 && lat <= 70 && lon >= -10 && lon <= 40) {
      region = 'Europe'
    } else if (lat >= -35 && lat <= 37 && lon >= -18 && lon <= 52) {
      region = 'Africa'
    } else if (lat >= -10 && lat <= 55 && lon >= 40 && lon <= 145) {
      region = 'Asia'
    } else if (lat >= -45 && lat <= -10 && lon >= 110 && lon <= 155) {
      region = 'Australia/Oceania'
    } else if (Math.abs(lon) > 150 || Math.abs(lon) < 30) {
      if (Math.abs(lat) < 50) {
        region = 'Pacific Ocean'
      }
    } else if (lon >= -70 && lon <= -20 && Math.abs(lat) < 55) {
      region = 'Atlantic Ocean'
    }

    return `${region} (${absLat}°${latDir}, ${absLon}°${lonDir})`
  }

  async function fetchAll() {
    const now = Date.now()
    if (now - lastFetchTime < 2000) {
      return
    }
    setLastFetchTime(now)
    setLoading(true)
    setInfo(null)
    setHasResults(false)
    
    try {
      const locationName = await fetchLocationName(latitude, longitude)
      setPlaceName(locationName)

      if (FRONTEND_ONLY) {
        const gibsUrl = `https://gibs-{s}.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/${dayjs(endDate).format('YYYY-MM-DD')}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`
        setThumbUrl(gibsUrl)
        setNdvi([])
        setPeaks([])
        setForecastDates([])
        setForecastValues([])
        setInfo('Frontend-only mode: showing public NDVI tiles. Time-series/forecast disabled.')
        setHasResults(true)
      } else {
        const [ndviRes, peaksRes, forecastRes, thumbRes, analysisRes] = await Promise.all([
          axios.post(`${API_BASE}/api/ndvi`, { ...requestBody }),
          axios.post(`${API_BASE}/api/peaks`, { ...requestBody, threshold }),
          axios.post(`${API_BASE}/api/forecast`, { ...requestBody, future_steps: futureSteps, look_back: 30 }),
          axios.post(`${API_BASE}/api/ndvi-thumb`, { ...requestBody }),
          axios.post(`${API_BASE}/api/analysis`, { ...requestBody, threshold, future_steps: futureSteps, look_back: 30 }).catch(() => null),
        ])
        setNdvi(ndviRes.data.records)
        setPeaks(peaksRes.data.peaks)
        if (forecastRes.data.skipped) {
          setInfo('Forecasting skipped: NDVI too low for reliable vegetation forecast.')
          setForecastDates([])
          setForecastValues([])
        } else {
          setForecastDates(forecastRes.data.dates)
          setForecastValues(forecastRes.data.values)
        }
        setThumbUrl(thumbRes.data.url ? `${thumbRes.data.url}${thumbRes.data.url.includes('?') ? '&' : '?'}ts=${Date.now()}` : '')
        if (analysisRes?.data?.success) {
          setAnalysis(analysisRes.data)
        }
        setHasResults(true)
      }
    } catch (e: any) {
      setInfo(e?.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const combinedSeries = useMemo(() => {
    const hist = ndvi.map(r => ({ date: r.Date.substring(0,10), historical: r.NDVI }))
    const lastHistDate = ndvi.length > 0 ? new Date(ndvi[ndvi.length - 1].Date) : new Date()
    const forecast = forecastDates
      .map((d, i) => ({ date: d.substring(0,10), forecast: forecastValues[i], dateObj: new Date(d) }))
      .filter(f => f.dateObj > lastHistDate)
      .map(({ date, forecast }) => ({ date, forecast }))
    
    const map: Record<string, { date: string; historical?: number; forecast?: number }> = {}
    hist.forEach(h => { map[h.date] = { ...(map[h.date] || { date: h.date }), historical: h.historical } })
    forecast.forEach(f => { map[f.date] = { ...(map[f.date] || { date: f.date }), forecast: f.forecast } })
    return Object.values(map).sort((a, b) => a.date.localeCompare(b.date))
  }, [ndvi, forecastDates, forecastValues])

  const peakPoints = useMemo(() => {
    if (!ndvi || ndvi.length === 0 || !peaks || peaks.length === 0) return [] as { date: string; peak: number }[]
    const pts: { date: string; peak: number }[] = []
    peaks.forEach(idx => {
      const rec = ndvi[idx]
      if (rec) pts.push({ date: rec.Date.substring(0,10), peak: rec.NDVI })
    })
    return pts
  }, [ndvi, peaks])

  const summary = useMemo(() => {
    if (!ndvi || ndvi.length === 0) return null as null | any

    const values = ndvi.map(r => r.NDVI)
    const dates = ndvi.map(r => r.Date.substring(0,10))
    const latestNdvi = values[values.length - 1]
    const mean = values.reduce((a,b)=>a+b,0) / values.length
    const min = Math.min(...values)
    const max = Math.max(...values)

    const vegType = (v: number) => {
      if (v >= 0.7) return 'Very Dense Vegetation'
      if (v >= 0.6) return 'Dense Vegetation'
      if (v >= 0.4) return 'Healthy Vegetation'
      if (v >= 0.2) return 'Sparse Vegetation'
      if (v >= 0.1) return 'Bare/Sparse'
      return 'Water/Non-vegetated'
    }

    const current = {
      vegetation_type: vegType(latestNdvi),
      health_status: latestNdvi >= 0.4 ? 'Growing' : (latestNdvi >= 0.2 ? 'Moderate' : 'Poor'),
      current_ndvi: latestNdvi.toFixed(2),
      description: latestNdvi >= 0.4 ? 'Vegetation is actively growing and in good health' : (latestNdvi >= 0.2 ? 'Vegetation is present but may be sparse' : 'Very low NDVI suggests bare ground or water')
    }

    const windowSize = Math.min(60, values.length)
    const rec = values.slice(-windowSize)
    const delta = rec[rec.length - 1] - rec[0]
    const trendLabel = Math.abs(delta) < 0.02 ? 'Stable' : (delta > 0 ? 'Improving' : 'Declining')
    const trends = {
      mean_ndvi: mean.toFixed(2),
      trend_direction: trendLabel,
      min_ndvi: min.toFixed(2),
      max_ndvi: max.toFixed(2)
    }

    let forecast: any = null
    if (forecastValues && forecastValues.length > 0) {
      const fMean = forecastValues.reduce((a,b)=>a+b,0) / forecastValues.length
      const fDelta = forecastValues[forecastValues.length - 1] - forecastValues[0]
      const fLabel = Math.abs(fDelta) < 0.02 ? 'Stable' : (fDelta > 0 ? 'Increasing' : 'Decreasing')
      const interp = fLabel === 'Increasing' ? 'Vegetation is expected to strengthen' : (fLabel === 'Decreasing' ? 'Vegetation may weaken' : 'Vegetation is expected to remain stable')
      forecast = {
        predicted_mean_ndvi: fMean.toFixed(2),
        forecast_trend: fLabel,
        forecast_interpretation: interp
      }
    } else if (info?.toLowerCase().includes('water')) {
      forecast = null
    }

    const peakItems: {date: string, value: string}[] = []
    if (peaks && peaks.length > 0) {
      const top = peaks.slice(0, 3)
      top.forEach(i => {
        const rec = ndvi[i]
        if (rec) peakItems.push({ date: rec.Date.substring(0,10), value: Number(rec.NDVI).toFixed(2) })
      })
    }

    const recommendations = getRecommendations(latestNdvi, delta, ndvi.length > 0 ? new Date(ndvi[ndvi.length - 1].Date).getMonth() + 1 : 1)

    return { current, trends, forecast, peaks: { count: peaks?.length || 0, items: peakItems }, recommendations, context: { roi: roiSize, lat: latitude, lon: longitude, start: startDate, end: endDate } }
  }, [ndvi, peaks, forecastValues, roiSize, latitude, longitude, startDate, endDate, info])

  const [roiColor, setRoiColor] = useState<string>('blue')

  useEffect(() => {
    if (!hasResults || !ndvi || ndvi.length === 0) return
    const latest = ndvi[ndvi.length - 1].NDVI
    if (latest >= 0.7) setRoiColor('#006400')
    else if (latest >= 0.6) setRoiColor('#228B22')
    else if (latest >= 0.4) setRoiColor('#32CD32')
    else if (latest >= 0.2) setRoiColor('#ADFF2F')
    else if (latest >= 0.1) setRoiColor('#FFFF00')
    else setRoiColor('#00BFFF')
  }, [ndvi, hasResults])

  function getRecommendations(ndvi: number, trend: number, month: number) {
    const recs = []
    
    if (ndvi < 0.1) {
      recs.push('Area appears to be water or bare land - not suitable for vegetation monitoring')
    } else if (ndvi < 0.2) {
      recs.push('Very sparse vegetation detected - consider irrigation or soil improvement')
      recs.push('Monitor for signs of drought stress')
    } else if (ndvi < 0.4) {
      recs.push('Moderate vegetation health - maintain regular monitoring')
      if (trend < -0.01) {
        recs.push('Declining trend detected - investigate potential stressors')
      }
    } else if (ndvi < 0.6) {
      recs.push('Healthy vegetation - continue current management practices')
      if (trend > 0.01) {
        recs.push('Positive growth trend - conditions are favorable')
      }
    } else {
      recs.push('Excellent vegetation health - peak growing conditions')
      recs.push('Monitor for optimal harvest timing if applicable')
    }

    if ([12, 1, 2].includes(month)) {
      recs.push('Winter season - expect lower NDVI values due to dormancy')
    } else if ([6, 7, 8].includes(month)) {
      recs.push('Summer season - monitor for heat stress and water availability')
    }

    return recs
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white">
      <header className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-brand to-brand-light opacity-10" />
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand text-white grid place-items-center shadow"><Leaf size={22} /></div>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">BloomWatch</h1>
              <p className="text-sm text-gray-600">MODIS NDVI Viewer and Forecast</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="card glass p-5 lg:col-span-1">
          <h2 className="text-lg font-medium mb-4">Settings</h2>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm text-gray-600">Latitude
              <input
                type="text"
                inputMode="decimal"
                className="mt-1 w-full border rounded px-2 py-1"
                value={latInput}
                onChange={e => {
                  const v = e.target.value
                  setLatInput(v)
                  const num = Number(v)
                  if (!Number.isNaN(num)) {
                    const clamped = Math.max(-90, Math.min(90, num))
                    setLatitude(clamped)
                  }
                }}
                onBlur={() => {
                  const num = Number(latInput)
                  const safe = Number.isNaN(num) ? latitude : Math.max(-90, Math.min(90, num))
                  setLatitude(safe)
                  setLatInput(String(safe))
                }}
                placeholder="e.g. -15.5"
              />
            </label>
            <label className="text-sm text-gray-600">Longitude
              <input
                type="text"
                inputMode="decimal"
                className="mt-1 w-full border rounded px-2 py-1"
                value={lonInput}
                onChange={e => {
                  const v = e.target.value
                  setLonInput(v)
                  const num = Number(v)
                  if (!Number.isNaN(num)) {
                    const clamped = Math.max(-180, Math.min(180, num))
                    setLongitude(clamped)
                  }
                }}
                onBlur={() => {
                  const num = Number(lonInput)
                  const safe = Number.isNaN(num) ? longitude : Math.max(-180, Math.min(180, num))
                  setLongitude(safe)
                  setLonInput(String(safe))
                }}
                placeholder="e.g. 30"
              />
            </label>
            <label className="text-sm text-gray-600">ROI Size (deg)
              <input type="number" className="mt-1 w-full border rounded px-2 py-1" value={roiSize} onChange={e=>setRoiSize(parseFloat(e.target.value))}/>
            </label>
            <label className="text-sm text-gray-600">Start Date
              <input type="date" className="mt-1 w-full border rounded px-2 py-1" value={startDate} onChange={e=>setStartDate(e.target.value)}/>
            </label>
            <label className="text-sm text-gray-600">End Date
              <input type="date" className="mt-1 w-full border rounded px-2 py-1" value={endDate} onChange={e=>setEndDate(e.target.value)}/>
            </label>
            <label className="text-sm text-gray-600">Bloom Threshold
              <input type="number" step="0.01" className="mt-1 w-full border rounded px-2 py-1" value={threshold} onChange={e=>setThreshold(parseFloat(e.target.value))}/>
            </label>
            <label className="text-sm text-gray-600">Forecast Days
              <input type="number" className="mt-1 w-full border rounded px-2 py-1" value={futureSteps} onChange={e=>setFutureSteps(parseInt(e.target.value))}/>
            </label>
          </div>
          <div className="mt-4">
            <button className="btn-primary w-full" onClick={fetchAll} disabled={loading}>{loading ? 'Loading…' : 'Run'}</button>
          </div>
          {info && <p className="mt-3 text-sm text-blue-700">{info}</p>}
        </section>

        <section className="card glass p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">NDVI Map</h2>
            <div className="flex items-center gap-2 flex-wrap">
              {placeName && (
                <span className="badge flex items-center gap-1">
                  <MapPin size={12} />
                  {locationLoading ? 'Locating...' : placeName}
                </span>
              )}
              <span className="badge">ROI {roiSize.toFixed(1)}°</span>
              <span className="badge">Detected Peaks {peaks?.length || 0}</span>
            </div>
          </div>
          <div className="h-80 overflow-hidden rounded-lg border-2 border-gray-200">
            <MapContainer
              key={`${latitude},${longitude},${roiSize}`}
              center={[latitude, longitude]}
              zoom={6}
              zoomControl={false}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              />
              <ZoomControl position="topright" zoomInTitle="Zoom in" zoomOutTitle="Zoom out" />
              {hasResults && thumbUrl && (
                <ImageOverlay
                  url={thumbUrl}
                  bounds={[[latitude - roiSize / 2, longitude - roiSize / 2], [latitude + roiSize / 2, longitude + roiSize / 2]]}
                  opacity={0.85}
                  interactive={false}
                />
              )}
              {hasResults && ndvi.length > 0 && (
                <Rectangle
                  bounds={[[latitude - roiSize/2, longitude - roiSize/2], [latitude + roiSize/2, longitude + roiSize/2]]}
                  pathOptions={{ color: roiColor, fillColor: roiColor, fillOpacity: 0.35 }}
                  interactive={false}
                />
              )}
            </MapContainer>
          </div>
        </section>

        <section className="card glass p-5 lg:col-span-3">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2">Time Series & Forecast</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={combinedSeries} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid stroke="#eee" strokeDasharray="5 5" />
                <XAxis dataKey="date" minTickGap={20} />
                <YAxis domain={[-0.1, 1]} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="historical" stroke="#1f77b4" dot={false} name="NDVI" />
                <Line type="monotone" dataKey="forecast" stroke="#ff7f0e" dot={false} name="Forecast" />
                {peakPoints.length > 0 && (
                  <Scatter data={peakPoints} dataKey="peak" name="NDVI Peaks" fill="#e11d48" shape="circle" />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {(hasResults && summary) && (
          <section className="card glass p-5 lg:col-span-3">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-medium">Vegetation Analysis Report</h2>
              <span className="badge">Source: NASA MODIS/GIBS</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
              <div>
                <h3 className="font-semibold text-green-700 mb-2">Vegetation Status</h3>
                <p><strong>Type:</strong> {summary.current.vegetation_type}</p>
                <p><strong>Health:</strong> {summary.current.health_status}</p>
                <p><strong>NDVI:</strong> {summary.current.current_ndvi}</p>
                <p className="text-gray-600 mt-1">{summary.current.description}</p>
              </div>
              <div>
                <h3 className="font-semibold text-blue-700 mb-2">NDVI Trends</h3>
                <p><strong>Average NDVI:</strong> {summary.trends.mean_ndvi}</p>
                <p><strong>Trend:</strong> {summary.trends.trend_direction}</p>
                <p><strong>Range:</strong> {summary.trends.min_ndvi} - {summary.trends.max_ndvi}</p>
                <p className="text-gray-600 mt-1 text-xs">Based on historical data from {summary.context.start} to {summary.context.end}</p>
              </div>
              <div>
                <h3 className="font-semibold text-purple-700 mb-2">NDVI Forecast</h3>
                {summary.forecast ? (
                  <>
                    <p><strong>Predicted NDVI:</strong> {summary.forecast.predicted_mean_ndvi}</p>
                    <p><strong>Trend:</strong> {summary.forecast.forecast_trend}</p>
                    <p className="text-gray-600 mt-1">{summary.forecast.forecast_interpretation}</p>
                  </>
                ) : (
                  <p className="text-gray-500">No forecast available for this region.</p>
                )}
              </div>
            </div>
            <div className="mt-6 p-4 bg-pink-50 rounded-lg border border-pink-200">
              <h3 className="font-semibold text-pink-700 mb-3">Detected Bloom Events</h3>
              <p className="text-sm text-gray-600 mb-2">Bloom events are local maxima in NDVI values, indicating periods of peak vegetation health and growth.</p>
              {summary.peaks.count > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {summary.peaks.items.map((p: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm bg-white p-2 rounded">
                      <span className="font-medium text-pink-700">Peak {i+1}:</span>
                      <span className="text-gray-700">{p.date}</span>
                      <span className="text-gray-500">(NDVI: {p.value})</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No peaks detected in the selected period. Try adjusting the bloom threshold or date range.</p>
              )}
            </div>
            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="font-semibold text-blue-700 mb-3">Recommendations</h3>
              {summary.recommendations && summary.recommendations.length > 0 ? (
                <ul className="space-y-2">
                  {summary.recommendations.map((rec: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-blue-600 mt-0.5">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 text-sm">No specific recommendations at this time.</p>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}