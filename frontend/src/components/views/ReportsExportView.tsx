import React from 'react';
import { 
  FileDown, 
  FileText, 
  Layers, 
  Database, 
  CheckCircle2, 
  Download, 
  ExternalLink,
  Printer,
  Share2,
  AlertTriangle
} from 'lucide-react';
import { FloodAnalysisResult } from '../../types';

interface ReportsExportViewProps {
  analysisResult: FloodAnalysisResult | null;
}

export const ReportsExportView: React.FC<ReportsExportViewProps> = ({
  analysisResult
}) => {
  if (!analysisResult) {
    return (
      <div className="p-8 text-center font-mono text-slate-400">
        Run flood analysis to generate exportable GIS rasters, vector shapes, and official briefing reports.
      </div>
    );
  }

  const handleDownloadReport = () => {
    if (analysisResult.report_download_url) {
      window.open(analysisResult.report_download_url, '_blank');
    }
  };

  const handleDownloadGeoTIFF = () => {
    if (analysisResult.raster_outputs?.geotiff) {
      window.open(analysisResult.raster_outputs.geotiff, '_blank');
    }
  };

  const handleDownloadGeoJSON = () => {
    if (analysisResult.vector_outputs?.geojson) {
      window.open(analysisResult.vector_outputs.geojson, '_blank');
    }
  };

  const handleDownloadJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(analysisResult, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `flood_analysis_${analysisResult.run_id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6 font-mono text-slate-200">
      {/* Low Coverage Warning Banner */}
      {analysisResult.low_coverage_warning && (
        <div className="hud-panel p-4 rounded-xl border border-amber-500/60 bg-amber-950/30 text-amber-200 space-y-1.5">
          <div className="flex items-center space-x-2 text-sm font-bold text-amber-400">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>LOW OBSERVATION COVERAGE WARNING ({analysisResult.valid_observation_percent}% OBSERVABLE)</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            {analysisResult.coverage_warning_message}
          </p>
        </div>
      )}

      {/* Title */}
      <div className="flex items-center justify-between border-b border-command-700/60 pb-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2.5">
            <FileDown className="w-5 h-5 text-cyan-glow" />
            <span>Disaster Reports &amp; Geospatial Exports</span>
          </h2>
          <div className="text-xs text-slate-400 mt-1">
            Reproducible GIS Rasters, GeoJSON Vectors, and DDMC Executive Briefings
          </div>
        </div>

        <div className="text-xs text-slate-400">
          Run ID: <code>{analysisResult.run_id}</code>
        </div>
      </div>

      {/* Primary Export Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* 1. Official Humanitarian Briefing Report */}
        <div className="hud-panel p-5 rounded-xl space-y-3 border-l-4 border-l-cyan-400 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-cyan-glow uppercase flex items-center space-x-1.5">
                <FileText className="w-4 h-4" />
                <span>Executive Response Briefing</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-glow font-bold">
                HTML / PDF PRINT
              </span>
            </div>

            <h3 className="text-sm font-bold text-white">
              District Disaster Management Committee (DDMC) Report
            </h3>

            <p className="text-xs text-slate-300 font-sans leading-relaxed">
              Complete situational intelligence summary with executive metrics, high-priority settlement impact register, infrastructure at risk, and certified ground accuracy statistics.
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={handleDownloadReport}
              className="w-full py-2.5 rounded bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold text-xs transition-all shadow-glow-cyan flex items-center justify-center space-x-2 cursor-pointer"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>OPEN OPERATIONAL BRIEFING REPORT</span>
            </button>
          </div>
        </div>

        {/* 2. Georeferenced GeoTIFF */}
        <div className="hud-panel p-5 rounded-xl space-y-3 border-l-4 border-l-[#ff3366] flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#ff3366] uppercase flex items-center space-x-1.5">
                <Layers className="w-4 h-4" />
                <span>Georeferenced Raster</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 font-bold">
                GEOTIFF &bull; EPSG:4326
              </span>
            </div>

            <h3 className="text-sm font-bold text-white">
              Newly Inundated Extent GeoTIFF
            </h3>

            <p className="text-xs text-slate-300 font-sans leading-relaxed">
              Standard 8-bit GeoTIFF with embedded affine geotransform, Deflate compression, and nodata masking. Direct drop-in for QGIS, ArcGIS Pro, and Google Earth Engine.
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={handleDownloadGeoTIFF}
              className="w-full py-2.5 rounded hud-panel hover:bg-command-800 text-xs text-cyan-glow font-bold border border-cyan-glow/40 transition-all flex items-center justify-center space-x-2 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>DOWNLOAD GEOTIFF (.TIF)</span>
            </button>
          </div>
        </div>

        {/* 3. GeoJSON Vector Footprint */}
        <div className="hud-panel p-5 rounded-xl space-y-3 border-l-4 border-l-purple-400 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-purple-400 uppercase flex items-center space-x-1.5">
                <Database className="w-4 h-4" />
                <span>Vector Feature Collection</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950 text-purple-300 font-bold">
                GEOJSON &bull; RFC 7946
              </span>
            </div>

            <h3 className="text-sm font-bold text-white">
              Vectorized Flood Inundation Polygons
            </h3>

            <p className="text-xs text-slate-300 font-sans leading-relaxed">
              Topology-preserved MultiPolygon vector boundaries simplified for web GIS viewports (MapLibre GL / Leaflet / Mapbox) with detection confidence attributes.
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={handleDownloadGeoJSON}
              className="w-full py-2.5 rounded hud-panel hover:bg-command-800 text-xs text-cyan-glow font-bold border border-cyan-glow/40 transition-all flex items-center justify-center space-x-2 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>DOWNLOAD VECTOR (.GEOJSON)</span>
            </button>
          </div>
        </div>

        {/* 4. Complete Analysis Metadata Envelope */}
        <div className="hud-panel p-5 rounded-xl space-y-3 border-l-4 border-l-emerald-400 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-400 uppercase flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>Provenance &amp; Parameters</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold">
                RAW JSON
              </span>
            </div>

            <h3 className="text-sm font-bold text-white">
              Full Scientific Analysis Envelope
            </h3>

            <p className="text-xs text-slate-300 font-sans leading-relaxed">
              Complete machine-readable JSON envelope containing input dates, thresholds, cloud percentages, confusion matrix statistics, and settlement impact records.
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={handleDownloadJSON}
              className="w-full py-2.5 rounded hud-panel hover:bg-command-800 text-xs text-cyan-glow font-bold border border-cyan-glow/40 transition-all flex items-center justify-center space-x-2 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>DOWNLOAD METADATA (.JSON)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Satellite Provenance & Mosaicing Summary */}
      <div className="hud-panel p-4 rounded-xl space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-cyan-glow font-bold uppercase">Satellite Data Provenance</span>
          {analysisResult.is_mosaic && (
            <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 font-bold text-[10px]">
              MOSAIC: {analysisResult.tiles_mosaicked?.join(' + ')}
            </span>
          )}
        </div>
        <div className="text-slate-300 grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Pre-Flood Observation:</span>
            <div className="font-mono text-[11px] text-white break-all">
              {analysisResult.pre_scenes && analysisResult.pre_scenes.length > 0
                ? analysisResult.pre_scenes.map(s => s.scene_id).join(', ')
                : analysisResult.pre_scene.scene_id}
            </div>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Post-Flood Observation:</span>
            <div className="font-mono text-[11px] text-white break-all">
              {analysisResult.post_scenes && analysisResult.post_scenes.length > 0
                ? analysisResult.post_scenes.map(s => s.scene_id).join(', ')
                : analysisResult.post_scene.scene_id}
            </div>
          </div>
        </div>

        {analysisResult.sar_result && (
          <div className="pt-2 border-t border-slate-800 text-slate-300 grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <span className="text-sky-400 block text-[10px] uppercase font-bold">Sentinel-1 Baseline SAR Scene:</span>
              <div className="font-mono text-[11px] text-white break-all">
                {analysisResult.sar_result.pre_scene.scene_id} ({analysisResult.sar_result.pre_scene.acquisition_date}, Orbit {analysisResult.sar_result.pre_scene.relative_orbit})
              </div>
            </div>
            <div>
              <span className="text-rose-400 block text-[10px] uppercase font-bold">Sentinel-1 Response SAR Scene:</span>
              <div className="font-mono text-[11px] text-white break-all">
                {analysisResult.sar_result.post_scene.scene_id} ({analysisResult.sar_result.post_scene.acquisition_date}, Orbit {analysisResult.sar_result.post_scene.relative_orbit})
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
