import React from 'react';
import { 
  Radio, 
  Satellite, 
  MapPin, 
  Calendar, 
  Activity, 
  FileText, 
  Settings, 
  ChevronDown,
  Layers,
  Sparkles
} from 'lucide-react';
import { StudyArea, FloodAnalysisResult, AnalysisRunRequest } from '../../types';

interface TopNavProps {
  studyAreas: StudyArea[];
  activeStudyArea: StudyArea;
  onSelectStudyArea: (area: StudyArea) => void;
  analysisResult: FloodAnalysisResult | null;
  activeParams?: AnalysisRunRequest | null;
  onOpenReports: () => void;
  onOpenSettings: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  studyAreas,
  activeStudyArea,
  onSelectStudyArea,
  analysisResult,
  activeParams,
  onOpenReports,
  onOpenSettings
}) => {
  return (
    <header className="h-16 border-b border-command-700/60 bg-command-950/90 backdrop-blur-md px-4 flex items-center justify-between z-40 relative">
      {/* Brand & Mission Title */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-black font-black shadow-glow-cyan">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="text-[10px] uppercase font-mono tracking-widest text-cyan-glow">
                Disaster Intelligence &bull; PS-01
              </span>
            </div>
            <h1 className="text-sm font-bold tracking-wider text-white uppercase font-mono">
              Nepal Terai Flood Intelligence
            </h1>
          </div>
        </div>

        {/* Study Basin Dropdown Selector */}
        <div className="flex items-center pl-3 lg:pl-4 border-l border-command-700/60">
          <div className="relative group">
            <button className="flex items-center space-x-2 px-3 py-1.5 rounded hud-panel hover:border-cyan-glow/40 transition-colors text-xs font-mono text-slate-200">
              <MapPin className="w-3.5 h-3.5 text-cyan-glow" />
              <span>{activeStudyArea.name}</span>
              <ChevronDown className="w-3 h-3 text-slate-400 group-hover:text-cyan-glow" />
            </button>

            {/* Dropdown Menu */}
            <div className="absolute top-full left-0 mt-1.5 w-84 max-h-[28rem] overflow-y-auto rounded hud-panel-glow py-1 shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-opacity z-50 divide-y divide-command-700/40">
              {/* Region-Wide Option */}
              {studyAreas.filter(a => a.area_type === 'region').length > 0 && (
                <div>
                  <div className="px-3 py-1 text-[9px] font-mono uppercase tracking-wider text-emerald-400 bg-emerald-950/20">
                    Regional Scale (Full Terai):
                  </div>
                  {studyAreas.filter(a => a.area_type === 'region').map((area) => (
                    <button
                      key={area.id}
                      onClick={() => onSelectStudyArea(area)}
                      className={`w-full text-left px-3 py-2 text-xs font-mono flex items-center justify-between hover:bg-emerald-500/10 transition-colors ${
                        activeStudyArea.id === area.id ? 'text-emerald-400 bg-emerald-950/40' : 'text-slate-200'
                      }`}
                    >
                      <div>
                        <span className="font-semibold block">{area.name}</span>
                        <span className="text-[10px] text-slate-500">{area.district}</span>
                      </div>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono">
                        REGION
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Hydrological Basins */}
              <div>
                <div className="px-3 py-1 text-[9px] font-mono uppercase tracking-wider text-cyan-glow bg-cyan-950/20">
                  Hydrological River Basins:
                </div>
                {studyAreas.filter(a => a.area_type === 'basin' || !a.area_type).map((area) => (
                  <button
                    key={area.id}
                    onClick={() => onSelectStudyArea(area)}
                    className={`w-full text-left px-3 py-2 text-xs font-mono flex items-center justify-between hover:bg-cyan-500/10 transition-colors ${
                      activeStudyArea.id === area.id ? 'text-cyan-glow bg-cyan-950/30' : 'text-slate-300'
                    }`}
                  >
                    <div>
                      <span className="font-semibold block">{area.name}</span>
                      <span className="text-[10px] text-slate-500">{area.district} &bull; {area.province}</span>
                    </div>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono">
                      BASIN
                    </span>
                  </button>
                ))}
              </div>

              {/* Administrative Districts */}
              {studyAreas.filter(a => a.area_type === 'district').length > 0 && (
                <div>
                  <div className="px-3 py-1 text-[9px] font-mono uppercase tracking-wider text-amber-400 bg-amber-950/20">
                    Administrative Districts ({studyAreas.filter(a => a.area_type === 'district').length}):
                  </div>
                  {studyAreas.filter(a => a.area_type === 'district').map((area) => (
                    <button
                      key={area.id}
                      onClick={() => onSelectStudyArea(area)}
                      className={`w-full text-left px-3 py-1.5 text-xs font-mono flex items-center justify-between hover:bg-amber-500/10 transition-colors ${
                        activeStudyArea.id === area.id ? 'text-amber-400 bg-amber-950/30' : 'text-slate-300'
                      }`}
                    >
                      <div>
                        <span className="font-semibold">{area.district || area.name}</span>
                        <span className="text-[10px] text-slate-500 ml-2">{area.province}</span>
                      </div>
                      <span className="text-[9px] px-1 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                        {area.pcode || 'DISTRICT'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Center Operational Metadata Readouts */}
      <div className="hidden md:flex items-center space-x-6 text-xs font-mono text-slate-300">
        {/* Observation Window */}
        <div className="flex items-center space-x-2">
          <Calendar className="w-3.5 h-3.5 text-cyan-glow" />
          <span className="text-slate-400">Event Window:</span>
          <span className="text-white font-medium">
            {activeParams
              ? `${activeParams.pre_flood_date_start} — ${activeParams.post_flood_date_end}`
              : (analysisResult
                  ? `${analysisResult.pre_scene.acquisition_date} — ${analysisResult.post_scene.acquisition_date}`
                  : 'Sept 15 — Oct 05, 2024')}
          </span>
        </div>

        {/* Satellite Ingestion Source */}
        <div className="flex items-center space-x-2">
          <Satellite className="w-3.5 h-3.5 text-cyan-glow" />
          <span className="text-slate-400">Sensor:</span>
          <span className="text-white font-medium">
            {(analysisResult?.sensor_mode || activeParams?.sensor_mode) === 'SENTINEL_1_SAR' 
              ? 'Sentinel-1 C-SAR (Native 10m)' 
              : (analysisResult?.sensor_mode || activeParams?.sensor_mode) === 'DUAL_SENSOR_SYNERGY' 
                ? 'Dual-Sensor S2+S1 (Native 10m)' 
                : 'Sentinel-2 L2A (Native 10m)'}
          </span>
        </div>

        {/* Backend & GEE Status */}
        <div className="flex items-center space-x-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-slate-400">Pipeline:</span>
          <span className="text-emerald-400 font-semibold">
            Active &bull; {activeStudyArea.id === 'west_rapti_banke' ? 'UTM 44N' : 'UTM 45N'}
          </span>
        </div>
      </div>

      {/* Right Quick Actions */}
      <div className="flex items-center space-x-2.5">
        <button
          onClick={onOpenReports}
          className="px-3 py-1.5 rounded hud-panel hover:border-cyan-glow/50 text-xs font-mono text-slate-300 hover:text-cyan-glow flex items-center space-x-1.5 transition-all shadow-md"
        >
          <FileText className="w-3.5 h-3.5 text-cyan-glow" />
          <span className="hidden sm:inline">DDMC REPORT</span>
        </button>

        <button
          onClick={onOpenSettings}
          className="p-1.5 rounded hud-panel hover:border-cyan-glow/50 text-slate-400 hover:text-cyan-glow transition-all"
          title="Data Sources & Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
