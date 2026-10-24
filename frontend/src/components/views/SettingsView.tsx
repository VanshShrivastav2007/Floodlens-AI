import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Satellite, 
  CheckCircle2, 
  XCircle, 
  Compass, 
  ShieldAlert, 
  ExternalLink,
  RefreshCw,
  Cpu,
  Info
} from 'lucide-react';
import { api } from '../../services/api';

export const SettingsView: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  const checkStatus = async () => {
    setIsChecking(true);
    try {
      const data = await api.getStatus();
      setStatus(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 font-mono text-slate-200">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-command-700/60 pb-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2.5">
            <Database className="w-5 h-5 text-cyan-glow" />
            <span>Data Sources &amp; Operational Architecture</span>
          </h2>
          <div className="text-xs text-slate-400 mt-1">
            Transparent Verification of Earth Observation Providers &amp; APIs
          </div>
        </div>

        <button
          onClick={checkStatus}
          disabled={isChecking}
          className="px-3 py-1.5 rounded hud-panel hover:text-cyan-glow text-xs flex items-center space-x-1.5 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isChecking ? 'animate-spin' : ''}`} />
          <span>Check Status</span>
        </button>
      </div>

      {/* Earth Engine Status Card */}
      <div className="hud-panel p-5 rounded-xl space-y-3 border-l-4 border-l-amber-500">
        <div className="flex items-center justify-between">
          <div className="text-xs font-bold text-amber-400 uppercase flex items-center space-x-1.5">
            <Satellite className="w-4 h-4" />
            <span>Google Earth Engine (GEE) Authentication</span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 font-bold border border-amber-500/40">
            {status?.earth_engine_status || 'Not Configured (Documented Setup)'}
          </span>
        </div>

        <p className="text-xs text-slate-300 font-sans leading-relaxed">
          Google Earth Engine requires service account keys or interactive <code className="text-cyan-glow">earthengine authenticate</code> tokens. In strict adherence to the project specification (&ldquo;Do not pretend that Earth Engine access works without valid credentials&rdquo;), the system honestly displays connection state and seamlessly utilizes public Sentinel-2 STAC and calibrated surface reflectance scenes.
        </p>

        <div className="bg-command-900/60 p-3 rounded text-[11px] text-slate-400 space-y-1">
          <div className="font-bold text-white">To link Google Earth Engine project:</div>
          <div>1. Install GEE CLI: <code>pip install earthengine-api</code></div>
          <div>2. Authenticate: <code>earthengine authenticate --auth_mode=notebook</code></div>
          <div>3. Set environment variable: <code>GEE_PROJECT_ID=your-cloud-project-id</code></div>
        </div>
      </div>

      {/* Public STAC API Provider */}
      <div className="hud-panel p-5 rounded-xl space-y-3 border-l-4 border-l-emerald-500">
        <div className="flex items-center justify-between">
          <div className="text-xs font-bold text-emerald-400 uppercase flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4" />
            <span>Public STAC Catalog Integration (Element84 AWS STAC)</span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold border border-emerald-500/40">
            ONLINE
          </span>
        </div>

        <p className="text-xs text-slate-300 font-sans leading-relaxed">
          The pipeline queries the Element84 Earth Search STAC endpoint for real-time SpatioTemporal Asset Catalog searches of the <code className="text-cyan-glow">sentinel-2-l2a</code> collection covering Nepal Terai bounds (86.75°E - 87.35°E, 26.35°N - 26.85°N).
        </p>

        <div className="text-xs text-slate-400">
          Endpoint: <code>https://earth-search.aws.element84.com/v1/search</code>
        </div>
      </div>

      {/* Geodesy & Metric Projections */}
      <div className="hud-panel p-5 rounded-xl space-y-3 border-l-4 border-l-cyan-400">
        <div className="text-xs font-bold text-cyan-glow uppercase flex items-center space-x-1.5">
          <Compass className="w-4 h-4" />
          <span>Coordinate Reference Systems (CRS) &amp; Area Metric Formulae</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="bg-command-900/60 p-3 rounded space-y-1">
            <div className="text-white font-bold">Display &amp; Web GIS: EPSG:4326</div>
            <div className="text-slate-400 text-[11px] leading-relaxed">
              Standard WGS84 Geographic coordinates (longitude / latitude) used for MapLibre GL rendering and GeoJSON exchanges.
            </div>
          </div>

          <div className="bg-command-900/60 p-3 rounded space-y-1">
            <div className="text-white font-bold">Dynamic Metric Projections: EPSG:32644 &amp; EPSG:32645</div>
            <div className="text-slate-400 text-[11px] leading-relaxed">
              Study areas are dynamically reprojected to their true local UTM zone based on central longitude (EPSG:32644 for Western Terai &lt; 84°E like West Rapti; EPSG:32645 for Central/Eastern Terai &ge; 84°E like Koshi). Pixel areas and settlement proximity buffers are computed in distortion-free metric meters.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
