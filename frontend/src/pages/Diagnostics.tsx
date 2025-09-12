import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, Database, Server, RefreshCcw, Clock } from 'lucide-react';

interface ComponentStatus {
  name: string;
  status: string;
  details: Record<string, any>;
  warnings?: string[];
}

interface DiagnosticsResponse {
  timestamp: string;
  components: ComponentStatus[];
  warnings: string[];
}

const STATUS_COLOR: Record<string, string> = {
  ok: 'bg-green-100 text-green-800 border-green-300',
  stale: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  offline: 'bg-red-100 text-red-800 border-red-300',
  'no-data': 'bg-gray-100 text-gray-800 border-gray-300',
  error: 'bg-red-100 text-red-800 border-red-300',
  missing: 'bg-red-100 text-red-800 border-red-300',
  unknown: 'bg-gray-100 text-gray-800 border-gray-300'
};

const Diagnostics: React.FC = () => {
  const [data, setData] = useState<DiagnosticsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  const fetchDiagnostics = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('http://localhost:8847/diagnostics/status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (e: any) {
      setError(e.message || 'Failed to load diagnostics');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => fetchDiagnostics(), 10000);
    return () => clearInterval(id);
  }, [autoRefresh]);

  const formatValue = (v: any) => {
    if (v === null || v === undefined || v === '') return '-';
    if (typeof v === 'number') return v.toLocaleString();
    if (typeof v === 'string' && v.length > 64) return v.slice(0, 64) + '…';
    return String(v);
  };

  const iconFor = (name: string) => {
    switch (name) {
      case 'database': return <Database className="h-5 w-5" />;
      case 'backend': return <Server className="h-5 w-5" />;
      case 'collector': return <Activity className="h-5 w-5" />;
      case 'processor_hourly': return <RefreshCcw className="h-5 w-5" />;
      case 'processor_daily': return <Clock className="h-5 w-5" />;
      case 'categories': return <Activity className="h-5 w-5" />;
      default: return <Activity className="h-5 w-5" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Diagnostics</h1>
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
            <span>Auto refresh (10s)</span>
          </label>
          <button onClick={fetchDiagnostics} className="btn-secondary">Refresh</button>
        </div>
      </div>

      {loading && <div className="p-4 bg-gray-50 rounded border border-gray-200">Loading diagnostics…</div>}
      {error && <div className="p-4 bg-red-50 rounded border border-red-200 text-red-800">{error}</div>}

      {data && (
        <>
          {data.warnings.length > 0 && (
            <div className="card border-yellow-300 bg-yellow-50">
              <h2 className="text-lg font-semibold text-yellow-900 mb-2 flex items-center"><AlertTriangle className="h-5 w-5 mr-2" /> Pipeline Warnings</h2>
              <ul className="list-disc pl-5 space-y-1 text-sm text-yellow-800">
                {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.components.map(c => (
                <div key={c.name} className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      {iconFor(c.name)}
                      <h3 className="font-semibold text-gray-800 capitalize">{c.name.replace('_', ' ')}</h3>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded border font-medium ${STATUS_COLOR[c.status] || STATUS_COLOR['unknown']}`}>{c.status}</span>
                  </div>
                  <div className="space-y-1 text-xs font-mono max-h-48 overflow-auto pr-1">
                    {Object.entries(c.details).map(([k,v]) => (
                      <div key={k} className="flex justify-between"><span className="text-gray-500 mr-2">{k}</span><span className="text-gray-800 truncate">{formatValue(v)}</span></div>
                    ))}
                  </div>
                  {c.warnings && c.warnings.length > 0 && (
                    <div className="mt-2 text-xs text-yellow-700 bg-yellow-100 border border-yellow-200 rounded p-2 space-y-1">
                      {c.warnings.map((w,i)=><div key={i}>{w}</div>)}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="card">
              <h2 className="text-lg font-semibold mb-3">Raw JSON</h2>
              <pre className="text-xs bg-gray-900 text-gray-100 p-3 rounded overflow-auto max-h-96">{JSON.stringify(data, null, 2)}</pre>
            </div>
        </>
      )}
    </div>
  );
};

export default Diagnostics;
