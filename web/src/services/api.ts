const API_BASE = import.meta.env.VITE_API_BASE_URL;

async function request(path: string, data?: any, method: string = 'POST') {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    body: data ? JSON.stringify(data) : undefined,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.statusText}`);
  }
  return res.json();
}

export const getHealth = () => request('/health', undefined, 'GET');
export const fetchNdvi = (regionData: any) => request('/api/ndvi', regionData);
export const fetchPeaks = (peaksData: any) => request('/api/peaks', peaksData);
export const fetchForecast = (forecastData: any) => request('/api/forecast', forecastData);
export const fetchAnalysis = (analysisData: any) => request('/api/analysis', analysisData);
