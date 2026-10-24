import React, { useState } from 'react';
import { 
  Cpu, 
  Play, 
  Sliders, 
  Calendar, 
  CloudRain, 
  Waves, 
  CheckCircle2, 
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Info,
  Radio,
  Layers,
  ShieldCheck,
  Search,
  Satellite,
  Plus,
  Minus,
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { api } from '../../services/api';
import { 
  StudyArea, 
  AnalysisRunRequest, 
  WaterIndexType, 
  DataSourceType,
  FloodAnalysisResult,
  SensorMode,
  SARPolarization
} from '../../types';

interface FloodAnalysisViewProps {
  studyArea: StudyArea;
  activeParams?: AnalysisRunRequest;
  onUpdateParams?: (params: AnalysisRunRequest) => void;
  onRunAnalysis: (params: AnalysisRunRequest) => void;
  analysisResult: FloodAnalysisResult | null;
  isLoading: boolean;
}

export const FloodAnalysisView: React.FC<FloodAnalysisViewProps> = ({
  studyArea,
  activeParams,
  onUpdateParams,
  onRunAnalysis,
  analysisResult,
  isLoading
}) => {
  const [params, setParams] = useState<AnalysisRunRequest>(() => ({
    study_area_id: studyArea.id,
    pre_flood_date_start: activeParams?.pre_flood_date_start || '2024-09-01',
    pre_flood_date_end: activeParams?.pre_flood_date_end || '2024-09-25',
    post_flood_date_start: activeParams?.post_flood_date_start || '2024-09-26',
    post_flood_date_end: activeParams?.post_flood_date_end || '2024-10-15',
    max_cloud_cover_percent: activeParams?.max_cloud_cover_percent ?? 50.0,
    min_valid_coverage_percent: activeParams?.min_valid_coverage_percent ?? 30.0,
    water_index: activeParams?.water_index || 'MNDWI',
    water_threshold: activeParams?.water_threshold ?? 0.05,
    filter_permanent_water: activeParams?.filter_permanent_water ?? true,
    min_mapping_unit_pixels: activeParams?.min_mapping_unit_pixels ?? 5,
    data_source: activeParams?.data_source || 'Sentinel-2 L2A (Harmonized)',
    enable_mosaicing: activeParams?.enable_mosaicing ?? true,
    sensor_mode: activeParams?.sensor_mode || 'SENTINEL_2_OPTICAL',
    sar_polarization: activeParams?.sar_polarization || 'VV',
    sar_threshold_db: activeParams?.sar_threshold_db ?? -15.5,
    sar_change_threshold_db: activeParams?.sar_change_threshold_db ?? -2.5
  }));

  // Synchronize when studyArea or activeParams change
  React.useEffect(() => {
    setParams(prev => ({
      ...prev,
      ...(activeParams || {}),
      study_area_id: studyArea.id
    }));
  }, [studyArea.id, activeParams]);

  const updateParams = (newParams: AnalysisRunRequest) => {
    setParams(newParams);
    if (onUpdateParams) {
      onUpdateParams(newParams);
    }
  };

  const [isSearchingScenes, setIsSearchingScenes] = useState<boolean>(false);
  const [discoveredScenes, setDiscoveredScenes] = useState<any[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [sceneSearchCatalog, setSceneSearchCatalog] = useState<string>('');

  const shiftDate = (dateStr: string, days: number): string => {
    try {
      const parts = dateStr.split('-');
      const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      d.setDate(d.getDate() + days);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    } catch {
      return dateStr;
    }
  };

  const isPreDateValid = params.pre_flood_date_start <= params.pre_flood_date_end;
  const isPostDateValid = params.post_flood_date_start <= params.post_flood_date_end;
  const isOrderValid = params.pre_flood_date_start <= params.post_flood_date_start;
  const areDatesValid = isPreDateValid && isPostDateValid && isOrderValid;

  const handleSearchScenes = async () => {
    setIsSearchingScenes(true);
    setSearchError(null);
    try {
      const res = await api.getSatelliteScenes({
        study_area_id: studyArea.id,
        date_start: params.pre_flood_date_start,
        date_end: params.post_flood_date_end,
        sensor_mode: params.sensor_mode,
        max_cloud_cover: params.max_cloud_cover_percent
      });
      setDiscoveredScenes(res.scenes || []);
      setSceneSearchCatalog(res.source || 'STAC Catalogs');
    } catch (err: any) {
      setSearchError(err?.message || 'Failed to search observations in STAC catalog');
      setDiscoveredScenes([]);
    } finally {
      setIsSearchingScenes(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading || !areDatesValid) return;
    onRunAnalysis({
      ...params,
      study_area_id: studyArea.id
    });
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 font-mono text-slate-200">
      {/* Low Observation Coverage Alert Banner */}
      {analysisResult?.low_coverage_warning && (
        <div className="hud-panel p-4 rounded-xl border-2 border-amber-500/60 bg-amber-950/30 text-amber-200 space-y-2">
          <div className="flex items-center space-x-2 text-sm font-bold text-amber-400">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>LOW OBSERVATION COVERAGE WARNING ({analysisResult.valid_observation_percent}% OBSERVABLE)</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            {analysisResult.coverage_warning_message}
          </p>
          <div className="text-[11px] text-amber-400/90 font-mono">
            Optical water detection represents only clear-sky gaps. Do not use as whole-basin total extent.
          </div>
        </div>
      )}

      {/* Title */}
      <div className="flex items-center justify-between border-b border-command-700/60 pb-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2.5">
            <Cpu className="w-5 h-5 text-cyan-glow" />
            <span>Flood Detection Engine Configuration</span>
          </h2>
          <div className="text-xs text-slate-400 mt-1">
            Active Study Domain: <strong className="text-cyan-glow">{studyArea.name}</strong> ({studyArea.district})
          </div>
        </div>

        <button
          onClick={() => updateParams({
            study_area_id: studyArea.id,
            pre_flood_date_start: '2024-09-01',
            pre_flood_date_end: '2024-09-25',
            post_flood_date_start: '2024-09-26',
            post_flood_date_end: '2024-10-15',
            max_cloud_cover_percent: 50.0,
            min_valid_coverage_percent: 30.0,
            water_index: 'MNDWI',
            water_threshold: 0.05,
            filter_permanent_water: true,
            min_mapping_unit_pixels: 5,
            data_source: 'Sentinel-2 L2A (Harmonized)',
            enable_mosaicing: true,
            sensor_mode: 'SENTINEL_2_OPTICAL',
            sar_polarization: 'VV',
            sar_threshold_db: -15.5,
            sar_change_threshold_db: -2.5
          })}
          className="px-3 py-1.5 rounded hud-panel hover:text-cyan-glow text-xs flex items-center space-x-1.5 text-slate-400 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Defaults</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Sensor Intelligence Architecture Selector */}
        <div className="hud-panel p-5 rounded-xl space-y-4">
          <div className="text-xs font-bold uppercase tracking-wider text-cyan-glow flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Radio className="w-4 h-4 text-cyan-glow" />
              <span>Sensor Intelligence Architecture</span>
            </div>
            <span className="text-[10px] text-slate-400">
              Copernicus Constellation (Optical + C-Band Radar)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              {
                id: 'SENTINEL_2_OPTICAL' as SensorMode,
                title: 'Sentinel-2 Optical (MSI)',
                badge: '10m Multi-Spectral',
                badgeColor: 'text-cyan-400 bg-cyan-950/60 border-cyan-800',
                desc: 'Surface reflectance (Green/NIR/SWIR). High spectral specificity for clear skies with SCL cloud masking and multi-granule mosaicing.'
              },
              {
                id: 'SENTINEL_1_SAR' as SensorMode,
                title: 'Sentinel-1 C-SAR Radar',
                badge: 'All-Weather / Cloud-Piercing',
                badgeColor: 'text-sky-300 bg-sky-950/60 border-sky-800',
                desc: 'Terrain-corrected γ⁰ backscatter (Planetary Computer RTC). Penetrates 100% of dense monsoon clouds via specular backscatter attenuation.'
              },
              {
                id: 'DUAL_SENSOR_SYNERGY' as SensorMode,
                title: 'Dual-Sensor Synergy',
                badge: 'Fused Multi-Sensor',
                badgeColor: 'text-fuchsia-300 bg-fuchsia-950/60 border-fuchsia-800',
                desc: 'Consensus fusion: Confirms optical detections with SAR, uncovers flood hidden under optical clouds, and preserves optical extent outside SAR swath.'
              }
            ].map(mode => {
              const isSelected = (params.sensor_mode || 'SENTINEL_2_OPTICAL') === mode.id;
              return (
                <div
                  key={mode.id}
                  onClick={() => updateParams({ ...params, sensor_mode: mode.id })}
                  className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-cyan-500/15 border-cyan-glow text-white shadow-glow-cyan'
                      : 'bg-command-900/40 border-command-700/60 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">{mode.title}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-semibold ${mode.badgeColor}`}>
                      {mode.badge}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-sans mt-2 leading-relaxed">
                    {mode.desc}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Date Ranges Card */}
        <div className="hud-panel p-5 rounded-xl space-y-4">
          <div className="text-xs font-bold uppercase tracking-wider text-cyan-glow flex items-center space-x-2">
            <Calendar className="w-4 h-4" />
            <span>Temporal Observation Windows (Nepal Terai Monsoon)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
            {/* Pre-Flood Baseline */}
            <div className="space-y-2 bg-command-900/60 p-4 rounded-lg border border-command-700/50">
              <div className="font-bold text-slate-200">Pre-Flood Baseline Period</div>
              <div className="text-[11px] text-slate-400">Captures normal riverbed channels before extreme flood surge</div>
              
              <div className="grid grid-cols-2 gap-2 pt-2">
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">Start Date:</label>
                  <input
                    type="date"
                    value={params.pre_flood_date_start}
                    onChange={(e) => updateParams({ ...params, pre_flood_date_start: e.target.value })}
                    className="w-full bg-command-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:border-cyan-glow focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">End Date:</label>
                  <input
                    type="date"
                    value={params.pre_flood_date_end}
                    onChange={(e) => updateParams({ ...params, pre_flood_date_end: e.target.value })}
                    className="w-full bg-command-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:border-cyan-glow focus:outline-none"
                  />
                </div>
              </div>

              {/* Expansion Helpers */}
              <div className="flex items-center space-x-1.5 pt-1 text-[10px]">
                <span className="text-slate-500">Expand window:</span>
                <button
                  type="button"
                  onClick={() => updateParams({ ...params, pre_flood_date_start: shiftDate(params.pre_flood_date_start, -7) })}
                  className="px-2 py-0.5 rounded bg-command-950 border border-slate-700 hover:border-cyan-glow text-slate-300"
                >
                  -7d start
                </button>
                <button
                  type="button"
                  onClick={() => updateParams({ ...params, pre_flood_date_end: shiftDate(params.pre_flood_date_end, 7) })}
                  className="px-2 py-0.5 rounded bg-command-950 border border-slate-700 hover:border-cyan-glow text-slate-300"
                >
                  +7d end
                </button>
              </div>
            </div>

            {/* Post-Flood Observation */}
            <div className="space-y-2 bg-command-900/60 p-4 rounded-lg border border-command-700/50">
              <div className="font-bold text-[#ff3366]">Post-Flood Inundation Period</div>
              <div className="text-[11px] text-slate-400">Captures peak inundation and overbank flow after heavy rainfall</div>
              
              <div className="grid grid-cols-2 gap-2 pt-2">
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">Start Date:</label>
                  <input
                    type="date"
                    value={params.post_flood_date_start}
                    onChange={(e) => updateParams({ ...params, post_flood_date_start: e.target.value })}
                    className="w-full bg-command-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:border-cyan-glow focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block mb-1">End Date:</label>
                  <input
                    type="date"
                    value={params.post_flood_date_end}
                    onChange={(e) => updateParams({ ...params, post_flood_date_end: e.target.value })}
                    className="w-full bg-command-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:border-cyan-glow focus:outline-none"
                  />
                </div>
              </div>

              {/* Expansion Helpers */}
              <div className="flex items-center space-x-1.5 pt-1 text-[10px]">
                <span className="text-slate-500">Expand window:</span>
                <button
                  type="button"
                  onClick={() => updateParams({ ...params, post_flood_date_start: shiftDate(params.post_flood_date_start, -7) })}
                  className="px-2 py-0.5 rounded bg-command-950 border border-slate-700 hover:border-rose-400 text-slate-300"
                >
                  -7d start
                </button>
                <button
                  type="button"
                  onClick={() => updateParams({ ...params, post_flood_date_end: shiftDate(params.post_flood_date_end, 7) })}
                  className="px-2 py-0.5 rounded bg-command-950 border border-slate-700 hover:border-rose-400 text-slate-300"
                >
                  +7d end
                </button>
              </div>
            </div>
          </div>

          {/* Validation Warning if dates are invalid */}
          {!areDatesValid && (
            <div className="p-2.5 rounded bg-rose-950/50 border border-rose-500/50 text-xs text-rose-300 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <div>
                <strong>Temporal Ordering Error:</strong> Baseline start must be &le; baseline end, and post-flood period must start during or after baseline.
              </div>
            </div>
          )}

          {/* Explicit Search Observations in STAC Catalog */}
          <div className="pt-3 border-t border-command-700/50 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <span className="text-xs font-semibold text-slate-200">Catalog Observation Search:</span>
                <span className="text-[11px] text-slate-400 block">Query genuine satellite scenes covering this basin and date range from public STAC archives.</span>
              </div>
              <button
                type="button"
                onClick={handleSearchScenes}
                disabled={isSearchingScenes || !areDatesValid}
                className="px-3.5 py-2 rounded-lg bg-command-900 hover:bg-command-800 border border-cyan-glow/50 text-cyan-glow hover:text-white text-xs font-semibold flex items-center space-x-2 transition-all shadow-md disabled:opacity-50"
              >
                {isSearchingScenes ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Searching STAC...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    <span>Search Observations</span>
                  </>
                )}
              </button>
            </div>

            {searchError && (
              <div className="p-2.5 rounded bg-rose-950/40 border border-rose-500/40 text-xs text-rose-300 flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{searchError}</span>
              </div>
            )}

            {discoveredScenes !== null && (
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Found <strong className="text-white">{discoveredScenes.length}</strong> genuine scenes in <span className="text-cyan-glow">{sceneSearchCatalog}</span>:</span>
                  {discoveredScenes.length === 0 && <span className="text-amber-400 text-[11px]">Tip: Try expanding the date window using the buttons above</span>}
                </div>

                {discoveredScenes.length > 0 && (
                  <div className="max-h-52 overflow-y-auto space-y-2 pr-1">
                    {discoveredScenes.map((sc: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg bg-command-950/80 border border-command-800 hover:border-slate-600 flex flex-wrap items-center justify-between gap-2 text-xs font-mono"
                      >
                        <div className="flex items-center space-x-2.5">
                          <Satellite className="w-4 h-4 text-cyan-glow shrink-0" />
                          <div>
                            <div className="text-white font-bold flex items-center space-x-2">
                              <span>{sc.acquisition_date}</span>
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-command-800 text-slate-300 font-normal">
                                {sc.platform || 'Sentinel'} &bull; {sc.sensor_type || 'Optical'}
                              </span>
                              {sc.cloud_cover_percent !== undefined && sc.cloud_cover_percent > 0 && (
                                <span className="text-[10px] text-amber-300">
                                  {sc.cloud_cover_percent.toFixed(1)}% cloud
                                </span>
                              )}
                              {sc.relative_orbit && (
                                <span className="text-[10px] text-sky-300">
                                  Orbit {sc.relative_orbit}
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] text-slate-500 truncate max-w-sm" title={sc.scene_id}>
                              {sc.scene_id}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          <button
                            type="button"
                            onClick={() => updateParams({
                              ...params,
                              pre_flood_date_start: shiftDate(sc.acquisition_date, -5),
                              pre_flood_date_end: sc.acquisition_date
                            })}
                            className="px-2 py-1 rounded hud-panel text-[10px] text-cyan-glow hover:bg-cyan-950/50 border border-cyan-glow/30"
                            title="Set as Pre-Flood Baseline Window"
                          >
                            Set as Baseline
                          </button>
                          <button
                            type="button"
                            onClick={() => updateParams({
                              ...params,
                              post_flood_date_start: sc.acquisition_date,
                              post_flood_date_end: shiftDate(sc.acquisition_date, 5)
                            })}
                            className="px-2 py-1 rounded hud-panel text-[10px] text-rose-300 hover:bg-rose-950/50 border border-rose-500/30"
                            title="Set as Post-Flood Observation Window"
                          >
                            Set as Post-Flood
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Algorithm & Water Index Selection (For Optical & Synergy Modes) */}
        {params.sensor_mode !== 'SENTINEL_1_SAR' && (
          <div className="hud-panel p-5 rounded-xl space-y-4">
            <div className="text-xs font-bold uppercase tracking-wider text-cyan-glow flex items-center space-x-2">
              <Waves className="w-4 h-4" />
              <span>Sentinel-2 Water Index &amp; Thresholding Strategy</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {[
                {
                  id: 'MNDWI' as WaterIndexType,
                  title: 'MNDWI (Recommended)',
                  formula: '(Green B03 - SWIR B11) / (Green + SWIR)',
                  desc: 'SWIR significantly suppresses built-up urban surfaces and wet mud shadows.'
                },
                {
                  id: 'NDWI' as WaterIndexType,
                  title: 'Standard NDWI',
                  formula: '(Green B03 - NIR B08) / (Green + NIR)',
                  desc: 'Classic McFeeters index using high NIR absorption by water.'
                },
                {
                  id: 'COMBINED' as WaterIndexType,
                  title: 'Ensemble Consensus',
                  formula: 'Mean(NDWI, MNDWI)',
                  desc: 'Ensemble consensus to minimize single-band optical noise.'
                }
              ].map((idx) => {
                const isSelected = params.water_index === idx.id;

                return (
                  <div
                    key={idx.id}
                    onClick={() => updateParams({ ...params, water_index: idx.id })}
                    className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                      isSelected 
                        ? 'bg-cyan-500/15 border-cyan-glow text-white shadow-glow-cyan' 
                        : 'bg-command-900/40 border-command-700/60 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <div className="text-xs font-bold text-cyan-glow">{idx.title}</div>
                    <div className="text-[10px] text-slate-300 font-mono mt-1">{idx.formula}</div>
                    <div className="text-[10px] text-slate-500 font-sans mt-1.5 leading-relaxed">{idx.desc}</div>
                  </div>
                );
              })}
            </div>

            {/* Threshold & MMU Sliders */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-3 border-t border-slate-800/80 text-xs">
              {/* Water Threshold Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <span>Water Threshold (&tau;):</span>
                  <span className="text-cyan-glow font-bold">{params.water_threshold}</span>
                </div>
                <input
                  type="range"
                  min="-0.10"
                  max="0.25"
                  step="0.01"
                  value={params.water_threshold}
                  onChange={(e) => updateParams({ ...params, water_threshold: parseFloat(e.target.value) })}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>-0.10 (Sensitive)</span>
                  <span>0.05 (Calibrated)</span>
                  <span>+0.25 (Strict)</span>
                </div>
              </div>

              {/* Minimum Mapping Unit */}
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <span>Minimum Mapping Unit (MMU):</span>
                  <span className="text-cyan-glow font-bold">
                    {params.min_mapping_unit_pixels} px (~{(params.min_mapping_unit_pixels * 1.655).toFixed(1)} ha / {(params.min_mapping_unit_pixels * 16554).toLocaleString()} m²)
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="20"
                  step="1"
                  value={params.min_mapping_unit_pixels}
                  onChange={(e) => updateParams({ ...params, min_mapping_unit_pixels: parseInt(e.target.value) })}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>1 px (Raw speckle)</span>
                  <span>5 px (Recommended)</span>
                  <span>20 px (Coarse)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sentinel-1 C-SAR Radar Configuration (For SAR & Synergy Modes) */}
        {(params.sensor_mode === 'SENTINEL_1_SAR' || params.sensor_mode === 'DUAL_SENSOR_SYNERGY') && (
          <div className="hud-panel p-5 rounded-xl space-y-4 border-l-4 border-l-sky-400">
            <div className="text-xs font-bold uppercase tracking-wider text-sky-300 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Radio className="w-4 h-4 text-sky-400" />
                <span>Sentinel-1 C-SAR Radar Inundation Parameters</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-sky-950 border border-sky-500/40 text-sky-300 font-bold">
                PLANETARY COMPUTER RTC &gamma;&deg;
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {[
                { id: 'VV' as SARPolarization, title: 'VV Polarization', desc: 'Standard copolarized mode. Maximizes specular water reflection attenuation.' },
                { id: 'VH' as SARPolarization, title: 'VH Polarization', desc: 'Cross-polarized mode. Highly sensitive to volume scattering from vegetation.' },
                { id: 'VV+VH' as SARPolarization, title: 'Dual VV+VH', desc: 'Composite dual-channel analysis for complex flooded agricultural canopy.' }
              ].map(pol => {
                const isSelected = (params.sar_polarization || 'VV') === pol.id;
                return (
                  <div
                    key={pol.id}
                    onClick={() => updateParams({ ...params, sar_polarization: pol.id })}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-sky-500/20 border-sky-400 text-white shadow-glow-sky'
                        : 'bg-command-900/40 border-command-700/60 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <div className="text-xs font-bold text-sky-300">{pol.title}</div>
                    <div className="text-[10px] text-slate-400 font-sans mt-1 leading-snug">{pol.desc}</div>
                  </div>
                );
              })}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-3 border-t border-slate-800/80 text-xs">
              {/* Backscatter Threshold Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <span>Specular Threshold (&tau;<sub>SAR</sub>):</span>
                  <span className="text-sky-300 font-bold">{params.sar_threshold_db ?? -15.5} dB</span>
                </div>
                <input
                  type="range"
                  min="-22.0"
                  max="-10.0"
                  step="0.5"
                  value={params.sar_threshold_db ?? -15.5}
                  onChange={(e) => updateParams({ ...params, sar_threshold_db: parseFloat(e.target.value) })}
                  className="w-full accent-sky-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>-22.0 dB (Deep water)</span>
                  <span>-15.5 dB (Calibrated)</span>
                  <span>-10.0 dB (Turbid)</span>
                </div>
              </div>

              {/* Temporal Backscatter Drop */}
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <span>Temporal Change Drop (&Delta;&gamma;&deg;):</span>
                  <span className="text-amber-300 font-bold">&le; {params.sar_change_threshold_db ?? -2.5} dB</span>
                </div>
                <input
                  type="range"
                  min="-5.0"
                  max="-1.0"
                  step="0.5"
                  value={params.sar_change_threshold_db ?? -2.5}
                  onChange={(e) => updateParams({ ...params, sar_change_threshold_db: parseFloat(e.target.value) })}
                  className="w-full accent-amber-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>-5.0 dB (Severe plunge)</span>
                  <span>-2.5 dB (Standard anomaly)</span>
                  <span>-1.0 dB (Minor change)</span>
                </div>
              </div>
            </div>

            <div className="text-[10px] text-slate-400 bg-sky-950/30 p-2.5 rounded border border-sky-800/40 leading-relaxed">
              <strong>All-Weather Radar Physics:</strong> C-band microwave (5.405 GHz) transmits through cloud and rain unhindered. Smooth open water specularly scatters incoming radar pulses away from the antenna, creating pronounced negative anomalies (&Delta;&gamma;&deg; &le; -2.5 dB). Filtered using a 3x3 spatial median speckle filter.
            </div>
          </div>
        )}

        {/* Quality & Filtering Toggles */}
        <div className="hud-panel p-5 rounded-xl space-y-3">
          <div className="text-xs font-bold uppercase tracking-wider text-cyan-glow flex items-center space-x-2">
            <CloudRain className="w-4 h-4" />
            <span>Preprocessing &amp; Quality Exclusions</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <label className="flex items-start space-x-3 bg-command-900/60 p-3 rounded-lg border border-command-700/50 cursor-pointer hover:border-slate-600 transition-colors">
              <input
                type="checkbox"
                checked={params.enable_mosaicing !== false}
                onChange={(e) => updateParams({ ...params, enable_mosaicing: e.target.checked })}
                className="mt-0.5 rounded bg-command-950 border-slate-700 text-cyan-500 focus:ring-0 w-4 h-4"
              />
              <div>
                <span className="font-bold text-white block">Multi-Granule Sentinel-2 Mosaicing</span>
                <span className="text-[11px] text-slate-400 leading-tight block mt-0.5">
                  Mosaics adjacent MGRS granules (e.g. 45RVK + 45RWK) across orbit passes to eliminate out-of-swath data loss.
                </span>
              </div>
            </label>

            <label className="flex items-start space-x-3 bg-command-900/60 p-3 rounded-lg border border-command-700/50 cursor-pointer hover:border-slate-600 transition-colors">
              <input
                type="checkbox"
                checked={params.filter_permanent_water}
                onChange={(e) => updateParams({ ...params, filter_permanent_water: e.target.checked })}
                className="mt-0.5 rounded bg-command-950 border-slate-700 text-cyan-500 focus:ring-0 w-4 h-4"
              />
              <div>
                <span className="font-bold text-white block">Filter Permanent Water Bodies</span>
                <span className="text-[11px] text-slate-400 leading-tight block mt-0.5">
                  Distinguishes recurrent baseline Saptakoshi channels to isolate true newly inundated disaster zones.
                </span>
              </div>
            </label>

            <div className="bg-command-900/60 p-3 rounded-lg border border-command-700/50 space-y-1.5">
              <div className="flex justify-between">
                <span className="font-bold text-white">Max Cloud Tolerance:</span>
                <span className="text-cyan-glow font-bold">{params.max_cloud_cover_percent}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                step="5"
                value={params.max_cloud_cover_percent}
                onChange={(e) => updateParams({ ...params, max_cloud_cover_percent: parseFloat(e.target.value) })}
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <div className="text-[10px] text-slate-500">
                Filters satellite observations exceeding this scene cloud percentage.
              </div>
            </div>

            <div className="bg-command-900/60 p-3 rounded-lg border border-command-700/50 space-y-1.5">
              <div className="flex justify-between">
                <span className="font-bold text-white">Min Coverage Reliability:</span>
                <span className="text-cyan-glow font-bold">{params.min_valid_coverage_percent ?? 30}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="60"
                step="5"
                value={params.min_valid_coverage_percent ?? 30}
                onChange={(e) => updateParams({ ...params, min_valid_coverage_percent: parseFloat(e.target.value) })}
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <div className="text-[10px] text-slate-500">
                Flags warning if cloud-free area is insufficient for full-basin estimate (default: 30%).
              </div>
            </div>
          </div>
        </div>

        {/* Submit Execution Button */}
        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-slate-400">
            Target Projection: <strong className="text-white">{studyArea.center[0] < 84 ? 'EPSG:32644 (WGS84 / UTM Zone 44N - West Nepal)' : 'EPSG:32645 (WGS84 / UTM Zone 45N - Central/East Nepal)'}</strong>
          </div>

          <button
            type="submit"
            disabled={isLoading || !areDatesValid}
            className="px-6 py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold text-sm tracking-wide transition-all shadow-glow-cyan flex items-center space-x-2.5 cursor-pointer disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-black" />
            <span>
              {isLoading 
                ? 'ANALYZING SATELLITE RASTERS...' 
                : !areDatesValid 
                  ? 'INVALID TEMPORAL DATES' 
                  : 'EXECUTE FLOOD INTELLIGENCE PIPELINE'}
            </span>
          </button>
        </div>
      </form>
    </div>
  );
};
