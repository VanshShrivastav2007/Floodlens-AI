import React, { useState } from 'react';
import { 
  Globe2, 
  AlertTriangle, 
  Waves, 
  MapPin, 
  Calendar, 
  ShieldAlert, 
  ArrowRight, 
  Satellite, 
  Sparkles,
  Info
} from 'lucide-react';
import { StudyArea, FloodAnalysisResult } from '../../types';

interface OverviewViewProps {
  studyAreas: StudyArea[];
  activeStudyArea: StudyArea;
  onSelectStudyArea: (area: StudyArea) => void;
  onNavigateToAnalysis: () => void;
  analysisResult: FloodAnalysisResult | null;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  studyAreas,
  activeStudyArea,
  onSelectStudyArea,
  onNavigateToAnalysis,
  analysisResult
}) => {
  const [areaFilter, setAreaFilter] = useState<'all' | 'basin' | 'district' | 'region'>('all');
  
  const filteredStudyAreas = studyAreas.filter(area => {
    if (areaFilter === 'all') return true;
    return (area.area_type || 'basin') === areaFilter;
  });

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8 font-sans text-slate-200">
      {/* Hero Banner */}
      <div className="hud-panel-glow p-8 rounded-xl relative overflow-hidden border border-cyan-glow/30">
        <div className="absolute -right-12 -top-12 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-glow/40 text-[11px] font-mono text-cyan-glow">
            <Sparkles className="w-3.5 h-3.5" />
            <span>PROBLEM STATEMENT 01 &bull; RAPID DISASTER INTELLIGENCE</span>
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-white font-mono">
            Rapid Flood Extent Mapping &amp; Settlement Impact Assessment for the Nepal Terai
          </h1>

          <p className="text-sm text-slate-300 leading-relaxed font-sans">
            The Nepal Terai represents the vulnerable southern lowland plains along the Indian border. 
            Monsoon torrents dropping from 8,848 meters elevation across the Himalayan crest funnel into 
            transboundary river basins within less than 150 kilometers, causing catastrophic annual inundation.
          </p>

          <div className="pt-2 flex flex-wrap gap-3 font-mono text-xs">
            <button
              onClick={onNavigateToAnalysis}
              className="px-5 py-2.5 rounded bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-semibold transition-all shadow-glow-cyan flex items-center space-x-2 cursor-pointer"
            >
              <span>CONFIGURE &amp; RUN ANALYSIS</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <div className="px-4 py-2.5 rounded hud-panel text-slate-300 flex items-center space-x-2">
              <Satellite className="w-4 h-4 text-cyan-glow" />
              <span>Native 10m GSD Assets &bull; Canonical Analysis Grid (~120m)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Terai Basins & Districts Grid */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-command-700/60 pb-3 gap-2">
          <div className="text-sm font-mono font-bold uppercase tracking-wider text-white flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-cyan-glow" />
            <span>Study Regions, Basins &amp; Districts in Nepal Terai</span>
          </div>

          {/* Area Type Filter Tabs */}
          <div className="flex items-center space-x-1.5 text-xs font-mono bg-command-900/80 p-1 rounded-lg border border-command-700/60">
            {(['all', 'basin', 'district', 'region'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setAreaFilter(tab)}
                className={`px-2.5 py-1 rounded uppercase tracking-wider transition-colors cursor-pointer ${
                  areaFilter === tab 
                    ? 'bg-cyan-500/20 text-cyan-glow font-bold border border-cyan-glow/40' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab === 'all' ? `All (${studyAreas.length})` : 
                 tab === 'basin' ? `Basins (${studyAreas.filter(a => (a.area_type || 'basin') === 'basin').length})` :
                 tab === 'district' ? `Districts (${studyAreas.filter(a => a.area_type === 'district').length})` :
                 `Region (${studyAreas.filter(a => a.area_type === 'region').length})`}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {filteredStudyAreas.map((area) => {
            const isSelected = activeStudyArea.id === area.id;
            const areaType = area.area_type || 'basin';

            return (
              <div
                key={area.id}
                onClick={() => onSelectStudyArea(area)}
                className={`p-4 rounded-xl cursor-pointer transition-all border ${
                  isSelected 
                    ? 'hud-panel-glow border-cyan-glow/60 shadow-glow-cyan' 
                    : 'hud-panel hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded ${
                    areaType === 'region' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                    areaType === 'district' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                    isSelected ? 'bg-cyan-500/20 text-cyan-glow' : 'bg-command-800 text-slate-400'
                  }`}>
                    {areaType === 'region' ? 'REGION' : areaType === 'district' ? (area.pcode || 'DISTRICT') : 'BASIN'}
                  </span>
                  {isSelected && (
                    <span className="text-[10px] font-mono text-cyan-glow font-bold">&bull; ACTIVE FOCUS</span>
                  )}
                </div>

                <h3 className="text-sm font-bold font-mono text-white mt-2.5">
                  {area.name}
                </h3>

                <p className="text-xs text-slate-400 mt-1.5 line-clamp-2 leading-relaxed">
                  {area.description}
                </p>

                <div className="mt-3 pt-2.5 border-t border-slate-800/80 text-[11px] font-mono text-slate-400 flex items-center justify-between">
                  <span>{area.province}</span>
                  {area.area_sqkm ? (
                    <span className="text-cyan-glow font-semibold">{Math.round(area.area_sqkm).toLocaleString()} km²</span>
                  ) : (
                    <span className="text-cyan-glow font-semibold">Zoom {area.default_zoom}x</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Historical Major Flood Catalog */}
      <div className="space-y-4">
        <div className="text-sm font-mono font-bold uppercase tracking-wider text-white flex items-center space-x-2 border-b border-command-700/60 pb-2">
          <Calendar className="w-4 h-4 text-cyan-glow" />
          <span>Major Terai Flood Events for Calibration &amp; Verification</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
          <div className="hud-panel p-4 rounded-lg space-y-2 border-l-4 border-l-rose-500">
            <div className="text-xs font-bold text-rose-400">2024 LATE MONSOON MEGAFLOOD</div>
            <div className="text-[11px] text-slate-400">Sept 26 — Oct 02, 2024</div>
            <p className="text-xs text-slate-300 font-sans">
              Historic record atmospheric depression over Koshi basin. Koshi Barrage peak discharge exceeded 661,000 cusecs, breaking 1968 records and inundating Sunsari and Saptari wards.
            </p>
            <div className="text-[11px] text-cyan-glow font-bold pt-1">
              Active Benchmark Event for this System
            </div>
          </div>

          <div className="hud-panel p-4 rounded-lg space-y-2 border-l-4 border-l-amber-500">
            <div className="text-xs font-bold text-amber-400">2017 TERAI MEGAFLOOD</div>
            <div className="text-[11px] text-slate-400">Aug 11 — Aug 20, 2017</div>
            <p className="text-xs text-slate-300 font-sans">
              Torrential continuous rainfall across eastern &amp; central Terai submerged Gaur municipality and affected over 460,000 residents across Rautahat and Sarlahi.
            </p>
          </div>

          <div className="hud-panel p-4 rounded-lg space-y-2 border-l-4 border-l-blue-500">
            <div className="text-xs font-bold text-blue-400">2008 KUSAHA EMBANKMENT BREACH</div>
            <div className="text-[11px] text-slate-400">Aug 18 — Aug 30, 2008</div>
            <p className="text-xs text-slate-300 font-sans">
              Eastern embankment of Saptakoshi breached at Paschim Kusaha (Sunsari), diverting the river channel eastward and displacing over 70,000 Nepali residents.
            </p>
          </div>
        </div>
      </div>

      {/* Analytical Methodology Brief */}
      <div className="hud-panel p-6 rounded-xl space-y-4">
        <h3 className="text-sm font-mono font-bold uppercase tracking-wider text-cyan-glow flex items-center space-x-2">
          <Info className="w-4 h-4" />
          <span>Scientific Optical Flood Detection Pipeline</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
          <div className="bg-command-900/60 p-3 rounded border border-command-700/50 space-y-1">
            <div className="text-cyan-glow font-bold">1. Sentinel-2 L2A Ingestion</div>
            <p className="text-slate-400 font-sans text-[11px]">
              Retrieves surface reflectance Green (B03), NIR (B08), SWIR (B11), and Scene Classification Layer (SCL).
            </p>
          </div>

          <div className="bg-command-900/60 p-3 rounded border border-command-700/50 space-y-1">
            <div className="text-cyan-glow font-bold">2. SCL Cloud Masking</div>
            <p className="text-slate-400 font-sans text-[11px]">
              Extracts high/medium probability clouds and cloud shadows to guarantee no false dry-land assumptions under cover.
            </p>
          </div>

          <div className="bg-command-900/60 p-3 rounded border border-command-700/50 space-y-1">
            <div className="text-cyan-glow font-bold">3. MNDWI Indexing &amp; MMU</div>
            <p className="text-slate-400 font-sans text-[11px]">
              Applies Modified NDWI (Green-SWIR)/(Green+SWIR), subtracts permanent baseline riverbed, and filters speckle noise.
            </p>
          </div>

          <div className="bg-command-900/60 p-3 rounded border border-command-700/50 space-y-1">
            <div className="text-cyan-glow font-bold">4. Dynamic UTM Geodesy &amp; Impact</div>
            <p className="text-slate-400 font-sans text-[11px]">
              Projects dynamically to EPSG:32644 (UTM 44N) or EPSG:32645 (UTM 45N) for distortion-free metric areas and settlement proximity buffers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
